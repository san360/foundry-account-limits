#!/usr/bin/env python3
"""
test_dataplane.py
=================

Proves that a Foundry account created by ``foundry_limit_test.py`` is not just an
ARM record but an actually *usable* inference endpoint.

Control-plane success (``provisioningState == Succeeded``) does not guarantee the
data plane works: the custom subdomain has to resolve, the model deployment has to
be live, and the caller needs a data-plane RBAC role. This script closes that gap.

It exercises, against each account:

  1. ``GET`` the account + its model deployments (control plane sanity).
  2. A **chat completion** against a text model  (default ``gpt-5.6-sol``).
  3. An **embedding**       against ``text-embedding-3-large``.

Auth is Microsoft Entra ID (``AzureCliCredential``) — no API keys are read or
written anywhere.

Required data-plane role on the account (or its resource group):
    "Cognitive Services OpenAI User"   or   "Cognitive Services User"

Usage
-----
    # One named account
    python tests/test_dataplane.py -g rg-foundry-limit-swedencentral \
        --account fdyswe-q5y95-001

    # Every account in the resource group matching a prefix
    python tests/test_dataplane.py -g rg-foundry-limit-swedencentral \
        --prefix fdyswe --max 5
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from typing import Any, Dict, Iterator, List, Optional

import requests
from azure.identity import AzureCliCredential, get_bearer_token_provider

ARM = "https://management.azure.com"
CS_API = "2026-07-01"
ARM_SCOPE = "https://management.azure.com/.default"
AI_SCOPE = "https://cognitiveservices.azure.com/.default"

CHAT_MODEL_CANDIDATES = ["gpt-5.6-sol", "gpt-5.4", "gpt-5.4-nano"]
EMBED_MODEL_CANDIDATES = ["text-embedding-3-large"]


def arm_get(cred: AzureCliCredential, url: str, params: Dict[str, str]) -> Dict[str, Any]:
    token = cred.get_token(ARM_SCOPE).token
    resp = requests.get(
        url if url.startswith("http") else f"{ARM}{url}",
        params=params,
        headers={"Authorization": f"Bearer {token}"},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()


def paged(cred: AzureCliCredential, url: str, params: Dict[str, str]) -> Iterator[Dict[str, Any]]:
    """ARM collections page at 50 entries — always follow nextLink."""
    next_url: Optional[str] = url
    first = True
    while next_url:
        payload = arm_get(cred, next_url, params if first else {})
        for item in payload.get("value", []):
            yield item
        next_url = payload.get("nextLink")
        first = False


def resolve_endpoint(account: Dict[str, Any]) -> Optional[str]:
    props = account.get("properties", {}) or {}
    endpoints = props.get("endpoints") or {}
    for key in (
        "Azure AI Model Inference API",
        "OpenAI Language Model Instance API",
        "Azure OpenAI Service",
    ):
        if endpoints.get(key):
            return endpoints[key].rstrip("/")
    return (props.get("endpoint") or "").rstrip("/") or None


def test_account(
    cred: AzureCliCredential,
    sub: str,
    rg: str,
    name: str,
    chat_model: Optional[str],
    embed_model: Optional[str],
) -> Dict[str, Any]:
    result: Dict[str, Any] = {"account": name, "checks": {}, "ok": False}

    base = f"/subscriptions/{sub}/resourceGroups/{rg}/providers/Microsoft.CognitiveServices/accounts/{name}"

    # --- 1. control plane -----------------------------------------------------
    try:
        account = arm_get(cred, base, {"api-version": CS_API})
        state = (account.get("properties", {}) or {}).get("provisioningState")
        endpoint = resolve_endpoint(account)
        result["checks"]["account"] = {
            "ok": state == "Succeeded" and bool(endpoint),
            "provisioningState": state,
            "endpoint": endpoint,
        }
        if not endpoint:
            result["error"] = "no data-plane endpoint on account"
            return result
    except Exception as exc:  # noqa: BLE001
        result["checks"]["account"] = {"ok": False, "error": str(exc)[:300]}
        return result

    try:
        deployments = list(paged(cred, f"{base}/deployments", {"api-version": CS_API}))
    except Exception as exc:  # noqa: BLE001
        result["checks"]["deployments"] = {"ok": False, "error": str(exc)[:300]}
        return result

    names = [d["name"] for d in deployments]
    result["checks"]["deployments"] = {
        "ok": bool(names),
        "count": len(names),
        "names": names,
        "states": {
            d["name"]: (d.get("properties", {}) or {}).get("provisioningState") for d in deployments
        },
    }

    chosen_chat = chat_model or next((m for m in CHAT_MODEL_CANDIDATES if m in names), None)
    chosen_embed = embed_model or next((m for m in EMBED_MODEL_CANDIDATES if m in names), None)

    # OpenAI-compatible client bound to Entra ID.
    try:
        from openai import AzureOpenAI
    except ImportError:
        result["error"] = "openai package not installed (pip install openai)"
        return result

    token_provider = get_bearer_token_provider(cred, AI_SCOPE)
    client = AzureOpenAI(
        azure_endpoint=endpoint,
        azure_ad_token_provider=token_provider,
        api_version="2024-10-21",
        max_retries=3,
    )

    # --- 2. chat completion ---------------------------------------------------
    if chosen_chat:
        started = time.time()
        try:
            completion = client.chat.completions.create(
                model=chosen_chat,
                messages=[
                    {"role": "user", "content": "Reply with exactly one word: pong"},
                ],
                max_completion_tokens=2048,
            )
            text = (completion.choices[0].message.content or "").strip()
            result["checks"]["chat"] = {
                "ok": bool(text),
                "model": chosen_chat,
                "reply": text[:120],
                "latency_s": round(time.time() - started, 2),
            }
        except Exception as exc:  # noqa: BLE001
            result["checks"]["chat"] = {
                "ok": False,
                "model": chosen_chat,
                "error": str(exc)[:400],
                "latency_s": round(time.time() - started, 2),
            }
    else:
        result["checks"]["chat"] = {"ok": False, "error": "no chat deployment found"}

    # --- 3. embedding ---------------------------------------------------------
    if chosen_embed:
        started = time.time()
        try:
            emb = client.embeddings.create(
                model=chosen_embed,
                input="Microsoft Foundry account limit test.",
            )
            vector = emb.data[0].embedding
            result["checks"]["embedding"] = {
                "ok": len(vector) > 0,
                "model": chosen_embed,
                "dimensions": len(vector),
                "latency_s": round(time.time() - started, 2),
            }
        except Exception as exc:  # noqa: BLE001
            result["checks"]["embedding"] = {
                "ok": False,
                "model": chosen_embed,
                "error": str(exc)[:400],
                "latency_s": round(time.time() - started, 2),
            }
    else:
        result["checks"]["embedding"] = {"ok": False, "error": "no embedding deployment found"}

    result["ok"] = all(c.get("ok") for c in result["checks"].values())
    return result


def main() -> int:
    p = argparse.ArgumentParser(description="Data-plane smoke test for Foundry accounts.")
    p.add_argument("--subscription", default="70356d4b-bebe-4358-8baa-5dbdaf412088")
    p.add_argument("--tenant", default="2bab7b85-25a5-40d1-a83e-77d201b4da49")
    p.add_argument("-g", "--resource-group", required=True)
    p.add_argument("--account", action="append", help="Account name (repeatable).")
    p.add_argument("--prefix", default=None, help="Test every account with this name prefix.")
    p.add_argument("--max", type=int, default=3, help="Cap how many accounts to test when using --prefix.")
    p.add_argument("--chat-model", default=None)
    p.add_argument("--embed-model", default=None)
    p.add_argument("--json-out", default=None)
    args = p.parse_args()

    cred = AzureCliCredential(tenant_id=args.tenant)
    sub, rg = args.subscription, args.resource_group

    targets: List[str] = list(args.account or [])
    if not targets:
        url = f"/subscriptions/{sub}/resourceGroups/{rg}/providers/Microsoft.CognitiveServices/accounts"
        found = [a["name"] for a in paged(cred, url, {"api-version": CS_API})]
        if args.prefix:
            found = [n for n in found if n.startswith(args.prefix)]
        targets = sorted(found)[: args.max]

    if not targets:
        print("No accounts to test.", file=sys.stderr)
        return 2

    print(f"Data-plane test — {len(targets)} account(s) in {rg}\n")
    results = []
    for name in targets:
        res = test_account(cred, sub, rg, name, args.chat_model, args.embed_model)
        results.append(res)

        status = "PASS" if res["ok"] else "FAIL"
        print(f"[{status}] {name}")
        for check, data in res["checks"].items():
            mark = "ok " if data.get("ok") else "ERR"
            detail = (
                data.get("reply")
                or (f"dims={data['dimensions']}" if data.get("dimensions") else None)
                or (f"{data.get('count')} deployment(s)" if "count" in data else None)
                or data.get("provisioningState")
                or data.get("error")
                or ""
            )
            latency = f" ({data['latency_s']}s)" if data.get("latency_s") else ""
            print(f"       {mark} {check:<12} {str(detail)[:110]}{latency}")
        print()

    passed = sum(1 for r in results if r["ok"])
    print(f"Summary: {passed}/{len(results)} account(s) fully usable.")

    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as fh:
            json.dump(results, fh, indent=2)
        print(f"Wrote {args.json_out}")

    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
