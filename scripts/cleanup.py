#!/usr/bin/env python3
"""
cleanup.py
==========

Tear down the Foundry accounts created by ``foundry_limit_test.py``.

Cognitive Services accounts **soft-delete**: after ``DELETE`` they are retained
for 48 hours and *continue to consume the regional account quota* until they are
purged. Any repeatable limit test therefore has to delete **and** purge, or the
next run starts with invisible ghosts eating its headroom.

Usage
-----
    # Preview what would be removed
    python scripts/cleanup.py -g rg-foundry-limit-swedencentral \
        --region swedencentral --dry-run

    # Delete + purge every fdy* account, then drop the resource group
    python scripts/cleanup.py -g rg-foundry-limit-swedencentral \
        --region swedencentral --purge --delete-group

    # Only remove accounts from one run
    python scripts/cleanup.py -g rg-foundry-limit-swedencentral \
        --region swedencentral --prefix fdycap --purge
"""

from __future__ import annotations

import argparse
import json
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, Iterator, List, Optional

import requests
from azure.identity import AzureCliCredential

ARM = "https://management.azure.com"
CS_API = "2026-07-01"
RG_API = "2021-04-01"
SCOPE = "https://management.azure.com/.default"


class TokenProvider:
    """Thread-safe ARM bearer-token cache with a 5-minute pre-expiry refresh."""

    def __init__(self, tenant: Optional[str] = None) -> None:
        self._cred = AzureCliCredential(tenant_id=tenant) if tenant else AzureCliCredential()
        self._lock = threading.Lock()
        self._token: Optional[str] = None
        self._expires: float = 0.0

    def __call__(self) -> str:
        with self._lock:
            if self._token is None or time.time() > self._expires - 300:
                tok = self._cred.get_token(SCOPE)
                self._token = tok.token
                self._expires = float(tok.expires_on)
            return self._token


def arm(
    token: TokenProvider,
    method: str,
    url: str,
    *,
    params: Optional[Dict[str, str]] = None,
    body: Optional[Dict[str, Any]] = None,
    timeout: int = 120,
    retries: int = 5,
) -> requests.Response:
    """ARM request with retry on 429 / 5xx, honouring Retry-After."""
    last: Optional[requests.Response] = None
    for attempt in range(retries):
        resp = requests.request(
            method,
            url if url.startswith("http") else f"{ARM}{url}",
            params=params,
            json=body,
            headers={
                "Authorization": f"Bearer {token()}",
                "Content-Type": "application/json",
            },
            timeout=timeout,
        )
        if resp.status_code != 429 and resp.status_code < 500:
            return resp
        last = resp
        wait = float(resp.headers.get("Retry-After", 2 ** attempt))
        time.sleep(min(wait, 60))
    return last if last is not None else resp


def paged(
    token: TokenProvider, url: str, params: Optional[Dict[str, str]] = None
) -> Iterator[Dict[str, Any]]:
    """Follow ARM ``nextLink`` pagination (collections page at 50 entries)."""
    next_url: Optional[str] = url
    first = True
    while next_url:
        resp = arm(token, "GET", next_url, params=params if first else None)
        if resp.status_code >= 400:
            raise RuntimeError(f"GET {next_url} -> {resp.status_code}: {resp.text[:400]}")
        payload = resp.json()
        for item in payload.get("value", []):
            yield item
        next_url = payload.get("nextLink")
        first = False


def list_accounts(token: TokenProvider, sub: str, rg: Optional[str]) -> List[Dict[str, Any]]:
    if rg:
        url = f"/subscriptions/{sub}/resourceGroups/{rg}/providers/Microsoft.CognitiveServices/accounts"
    else:
        url = f"/subscriptions/{sub}/providers/Microsoft.CognitiveServices/accounts"
    return list(paged(token, url, {"api-version": CS_API}))


def list_deleted(token: TokenProvider, sub: str) -> List[Dict[str, Any]]:
    url = f"/subscriptions/{sub}/providers/Microsoft.CognitiveServices/deletedAccounts"
    try:
        return list(paged(token, url, {"api-version": CS_API}))
    except RuntimeError:
        return []


def list_projects(token: TokenProvider, account_id: str) -> List[Dict[str, Any]]:
    """Child projects of a Foundry account."""
    try:
        return list(paged(token, f"{account_id}/projects", {"api-version": CS_API}))
    except RuntimeError:
        return []


def delete_projects(token: TokenProvider, account_id: str) -> List[str]:
    """Delete every child project and wait for each to disappear.

    A Foundry account cannot be deleted while it still has projects: ARM returns
    ``CannotDeleteResource`` ("Cannot delete resource while nested resources
    exist"). Basic-mode accounts always carry at least ``proj-default``, so this
    step is mandatory, not defensive.
    """
    problems: List[str] = []
    for proj in list_projects(token, account_id):
        pid = proj.get("id")
        pname = (pid or "").rsplit("/", 1)[-1]
        if not pid:
            continue
        resp = arm(token, "DELETE", pid, params={"api-version": CS_API})
        if resp.status_code >= 400 and resp.status_code != 404:
            problems.append(f"project {pname}: {resp.text[:200]}")
            continue
        deadline = time.time() + 300
        while time.time() < deadline:
            check = arm(token, "GET", pid, params={"api-version": CS_API})
            if check.status_code == 404:
                break
            time.sleep(5)
        else:
            problems.append(f"project {pname}: timeout waiting for delete")
    return problems


def delete_account(token: TokenProvider, account_id: str) -> Dict[str, Any]:
    """DELETE an account (and its child projects first) and poll until gone."""
    name = account_id.rsplit("/", 1)[-1]

    problems = delete_projects(token, account_id)
    if problems:
        return {
            "name": name,
            "action": "delete",
            "ok": False,
            "detail": "; ".join(problems)[:300],
        }

    resp = arm(token, "DELETE", account_id, params={"api-version": CS_API})
    if resp.status_code >= 400:
        return {"name": name, "action": "delete", "ok": False, "detail": resp.text[:300]}

    # 202 => long-running; poll the resource until it 404s.
    deadline = time.time() + 900
    while time.time() < deadline:
        check = arm(token, "GET", account_id, params={"api-version": CS_API})
        if check.status_code == 404:
            return {"name": name, "action": "delete", "ok": True}
        time.sleep(5)
    return {"name": name, "action": "delete", "ok": False, "detail": "timeout waiting for delete"}


def purge_by_id(token: TokenProvider, deleted_id: str) -> Dict[str, Any]:
    """Purge a soft-deleted account so it stops consuming the regional cap."""
    name = deleted_id.rsplit("/", 1)[-1]
    resp = arm(token, "DELETE", deleted_id, params={"api-version": CS_API})
    ok = resp.status_code in (200, 202, 204, 404)
    return {
        "name": name,
        "action": "purge",
        "ok": ok,
        "detail": None if ok else resp.text[:300],
    }


def main() -> int:
    p = argparse.ArgumentParser(description="Delete and purge Foundry limit-test accounts.")
    p.add_argument("--subscription", default="70356d4b-bebe-4358-8baa-5dbdaf412088")
    p.add_argument("--tenant", default="2bab7b85-25a5-40d1-a83e-77d201b4da49")
    p.add_argument("-g", "--resource-group", help="Required unless --purge-only.")
    p.add_argument("--region", default="swedencentral")
    p.add_argument("--prefix", default="fdy", help="Only touch accounts whose name starts with this.")
    p.add_argument("--parallel", type=int, default=10)
    p.add_argument("--purge", action="store_true", help="Also purge soft-deleted accounts.")
    p.add_argument(
        "--purge-only",
        action="store_true",
        help=(
            "Skip deletion; only purge soft-deleted accounts. Use when the resource "
            "group was already deleted -- its cascade soft-deletes the accounts, which "
            "keep consuming the regional cap until they are purged."
        ),
    )
    p.add_argument("--delete-group", action="store_true", help="Delete the resource group at the end.")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    if args.purge_only:
        args.purge = True
    elif not args.resource_group:
        p.error("-g/--resource-group is required unless --purge-only is given")

    token = TokenProvider(args.tenant)
    sub = args.subscription

    accounts = (
        []
        if args.purge_only
        else [
            a
            for a in list_accounts(token, sub, args.resource_group)
            if a.get("name", "").startswith(args.prefix)
        ]
    )
    print(f"Resource group : {args.resource_group or '(purge-only)'}")
    print(f"Region         : {args.region}")
    print(f"Prefix filter  : {args.prefix}")
    print(f"Accounts found : {len(accounts)}")
    for a in accounts:
        print(f"  - {a['name']}  ({a.get('location')})")

    if args.dry_run:
        print("\n[dry-run] nothing deleted.")
        if args.purge:
            ghosts = [d for d in list_deleted(token, sub) if d.get("name", "").startswith(args.prefix)]
            print(f"[dry-run] soft-deleted accounts that would be purged: {len(ghosts)}")
            for d in ghosts:
                print(f"  - {d['name']}  ({d.get('location')})")
        return 0

    results: List[Dict[str, Any]] = []
    if accounts:
        print(f"\nDeleting {len(accounts)} account(s) with parallelism {args.parallel} ...")
        with ThreadPoolExecutor(max_workers=args.parallel) as pool:
            futures = {pool.submit(delete_account, token, a["id"]): a["name"] for a in accounts}
            for fut in as_completed(futures):
                res = fut.result()
                results.append(res)
                flag = "OK  " if res["ok"] else "FAIL"
                print(f"  [{flag}] delete {res['name']} {res.get('detail') or ''}")

    if args.purge:
        # Soft-deleted accounts keep consuming the regional quota for 48h.
        time.sleep(5)
        ghosts = [
            d
            for d in list_deleted(token, sub)
            if d.get("name", "").startswith(args.prefix)
            and (d.get("location") or "").lower() == args.region.lower()
        ]
        print(f"\nPurging {len(ghosts)} soft-deleted account(s) ...")
        with ThreadPoolExecutor(max_workers=args.parallel) as pool:
            futures = [pool.submit(purge_by_id, token, d["id"]) for d in ghosts]
            for fut in as_completed(futures):
                res = fut.result()
                results.append(res)
                flag = "OK  " if res["ok"] else "FAIL"
                print(f"  [{flag}] purge  {res['name']} {res.get('detail') or ''}")

    if args.delete_group:
        print(f"\nDeleting resource group {args.resource_group} ...")
        resp = arm(
            token,
            "DELETE",
            f"/subscriptions/{sub}/resourcegroups/{args.resource_group}",
            params={"api-version": RG_API},
        )
        print(f"  -> HTTP {resp.status_code} (async; completion happens in the background)")

    failures = [r for r in results if not r["ok"]]
    print(f"\nDone. {len(results) - len(failures)} succeeded, {len(failures)} failed.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
