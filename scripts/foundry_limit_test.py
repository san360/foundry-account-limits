#!/usr/bin/env python3
"""
foundry_limit_test.py
=====================

Empirically determine the maximum number of Microsoft Foundry accounts
("basic mode" / basic agent setup) that can be deployed into a single Azure
subscription + region, and provision them into one resource group.

What it does
------------
1. Preflight: verifies subscription access, resource-provider registration,
   region support, model + Global Standard SKU availability, and reads the
   current model-capacity quota for the region.
2. Creates (or reuses) a single resource group.
3. Fans out N ARM deployments of ``infra/foundry-account.bicep`` with a bounded
   thread pool. Each deployment provisions:
       - 1 Foundry account  (Microsoft.CognitiveServices/accounts, kind=AIServices,
                              allowProjectManagement=true)
       - 1 Foundry project  (basic agent setup - Microsoft-managed storage)
       - N Global Standard model deployments
4. Classifies every failure (account-count cap vs. model quota vs. capacity vs.
   transient) and stops early once the hard cap is confirmed.
5. Writes a JSON result set and a Markdown report to ``results/``.

Auth uses the Azure CLI credential, so run ``az login --tenant <tenant>`` first.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import random
import re
import string
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field, asdict
from typing import Any

import requests
from azure.identity import AzureCliCredential

ARM = "https://management.azure.com"
ARM_SCOPE = "https://management.azure.com/.default"

DEPLOYMENTS_API = "2021-04-01"
COGSVC_API = "2026-07-01"
RG_API = "2021-04-01"

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
BICEP_FILE = REPO_ROOT / "infra" / "foundry-account.bicep"
ARM_JSON_FILE = REPO_ROOT / "infra" / "foundry-account.json"

# Error codes/messages that indicate a *hard* per-subscription/per-region cap on
# the number of Foundry (Cognitive Services) accounts. Hitting these means we
# found the limit and should stop.
#
# VERIFIED against a real run in swedencentral on 2026-09-09 (see
# results/foundry-limit-swedencentral-*.json). When the 100-account regional cap
# is reached, ARM returns error code ``InsufficientQuota`` with the message:
#
#     "Insufficient quota. Cannot create/update/move resource '<accountName>'."
#
# It surfaces through two different envelopes depending on timing:
#   * ``InvalidTemplateDeployment/InsufficientQuota`` - rejected at preflight
#     validation (fast, ~3s), the common case once the cap is already full.
#   * ``DeploymentFailed/InsufficientQuota``          - passed preflight while
#     headroom still existed, then lost the race at resource-creation time
#     (~20s). Same root cause, later envelope.
#
# Note the message names the *account* resource, never a model deployment. That
# is what separates it from model-capacity (TPM) quota exhaustion, which is a
# different limit entirely.
ACCOUNT_CAP_PATTERNS = [
    r"exceed.*(number|count).*(account|resource)",
    r"(account|resource).*(count|number).*(exceed|limit|quota)",
    r"maximum number of accounts",
    r"cannot create more than",
    r"ResourceQuotaExceeded",
    r"SubscriptionResourceCountExceeded",
    r"ResourceCountExceedsLimitDueToTemplate",
]

# Model-capacity (TPM) quota exhaustion - a *different* limit than account count.
# ``InsufficientQuota`` alone is deliberately NOT listed here: it is the shared
# code for both failure modes, so it is disambiguated in classify() by looking at
# which resource the message names.
MODEL_QUOTA_PATTERNS = [
    r"exceed.*quota.*(tokens|capacity|TPM)",
    r"current quota",
    r"quota.*exceeded.*deployment",
    r"InsufficientQuota",
]

# Indicators that an InsufficientQuota error is about model capacity rather than
# the account count: it names a model, a deployment SKU, or a capacity/TPM figure.
#
# These must be SPECIFIC. A bare "deployment ... quota" is useless because ARM's
# generic failure envelope always reads "At least one resource deployment
# operation failed ... | Insufficient quota", where "deployment" means the ARM
# deployment, not a model deployment - that wording appears verbatim in genuine
# account-cap failures too.
MODEL_SCOPED_HINTS = [
    r"capacity\s+of\s+quota",
    r"\bcapacity\b",
    r"\bTPM\b",
    r"tokens per minute",
    r"quota.*\bSKU\b",
    r"\bSKU\b.*quota",
    r"requested\s+\d+.*available\s+\d+",
    r"accounts/deployments",
    r"\bmodel\b.*\bquota\b",
]

CAPACITY_PATTERNS = [
    r"SpecialFeatureOrQuotaIdRequired",
    r"capacity",
    r"ServiceUnavailable",
]

TRANSIENT_PATTERNS = [
    r"Conflict",
    r"TooManyRequests",
    r"429",
    r"InternalServerError",
    r"GatewayTimeout",
    r"OperationNotComplete",
]


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
class TokenProvider:
    """Thread-safe ARM bearer-token cache on top of AzureCliCredential."""

    def __init__(self, tenant_id: str | None = None) -> None:
        self._cred = AzureCliCredential(tenant_id=tenant_id) if tenant_id else AzureCliCredential()
        self._lock = threading.Lock()
        self._token = None
        self._expires_on = 0.0

    def bearer(self) -> str:
        with self._lock:
            # Refresh 5 minutes before expiry.
            if self._token is None or time.time() > self._expires_on - 300:
                tok = self._cred.get_token(ARM_SCOPE)
                self._token = tok.token
                self._expires_on = float(tok.expires_on)
            return self._token


TOKENS: TokenProvider | None = None


def arm(
    method: str,
    url: str,
    *,
    params: dict | None = None,
    body: dict | None = None,
    timeout: int = 120,
    max_retries: int = 6,
) -> requests.Response:
    """ARM request with bearer auth, throttling-aware retry and backoff."""
    assert TOKENS is not None
    if url.startswith("/"):
        url = ARM + url
    attempt = 0
    while True:
        attempt += 1
        headers = {
            "Authorization": f"Bearer {TOKENS.bearer()}",
            "Content-Type": "application/json",
        }
        try:
            resp = requests.request(
                method, url, headers=headers, params=params, json=body, timeout=timeout
            )
        except requests.RequestException as exc:
            if attempt > max_retries:
                raise
            time.sleep(min(2**attempt, 30) + random.uniform(0, 2))
            continue

        # Retry on throttling / transient server errors.
        if resp.status_code in (429, 500, 502, 503, 504) and attempt <= max_retries:
            wait = float(resp.headers.get("Retry-After", 0)) or min(2**attempt, 60)
            time.sleep(wait + random.uniform(0, 2))
            continue
        return resp


# ---------------------------------------------------------------------------
# Result model
# ---------------------------------------------------------------------------
@dataclass
class AttemptResult:
    index: int
    account_name: str
    deployment_name: str
    status: str = "Unknown"          # Succeeded | Failed | Error
    classification: str = ""         # ok | account-cap | model-quota | capacity | transient | other
    duration_s: float = 0.0
    error_code: str = ""
    error_message: str = ""
    endpoint: str = ""
    provisioned_models: list[str] = field(default_factory=list)
    started_utc: str = ""
    finished_utc: str = ""


def classify(text: str, account_name: str = "") -> str:
    """Bucket an ARM failure.

    ``account_name`` matters: the regional account cap and model-capacity
    exhaustion share the ``InsufficientQuota`` error code, and the only reliable
    discriminator is *which resource the message names*. If the message says it
    cannot create the Foundry account itself, we hit the account cap.
    """
    if not text:
        return "other"

    for pat in ACCOUNT_CAP_PATTERNS:
        if re.search(pat, text, re.IGNORECASE):
            return "account-cap"

    # Disambiguate the shared InsufficientQuota code.
    if re.search(r"insufficient\s+quota", text, re.IGNORECASE):
        names_account = account_name and re.search(
            r"create/update/move\s+resource\s+'" + re.escape(account_name) + r"'",
            text,
            re.IGNORECASE,
        )
        # Fall back to the generic shape when the caller didn't supply a name.
        names_any_account = re.search(
            r"cannot\s+create/update/move\s+resource\b", text, re.IGNORECASE
        )
        model_scoped = any(re.search(p, text, re.IGNORECASE) for p in MODEL_SCOPED_HINTS)
        if (names_account or names_any_account) and not model_scoped:
            return "account-cap"
        return "model-quota"

    for pat in MODEL_QUOTA_PATTERNS:
        if re.search(pat, text, re.IGNORECASE):
            return "model-quota"
    for pat in CAPACITY_PATTERNS:
        if re.search(pat, text, re.IGNORECASE):
            return "capacity"
    for pat in TRANSIENT_PATTERNS:
        if re.search(pat, text, re.IGNORECASE):
            return "transient"
    return "other"


def flatten_error(obj: Any, depth: int = 0) -> tuple[str, str]:
    """Pull (code, message) out of a nested ARM error object."""
    if not isinstance(obj, dict) or depth > 6:
        return "", json.dumps(obj)[:2000] if obj else ""
    code = obj.get("code", "") or ""
    msg = obj.get("message", "") or ""
    details = obj.get("details") or obj.get("error") or []
    if isinstance(details, dict):
        details = [details]
    for d in details:
        c2, m2 = flatten_error(d, depth + 1)
        if c2:
            code = f"{code}/{c2}" if code else c2
        if m2:
            msg = f"{msg} | {m2}" if msg else m2
    return code, msg[:4000]


# ---------------------------------------------------------------------------
# Azure operations
# ---------------------------------------------------------------------------
def build_template() -> dict:
    """Compile the Bicep template to ARM JSON (falls back to a prebuilt JSON)."""
    try:
        subprocess.run(
            ["az", "bicep", "build", "--file", str(BICEP_FILE), "--outfile", str(ARM_JSON_FILE)],
            check=True,
            capture_output=True,
            shell=(os.name == "nt"),
        )
    except Exception as exc:  # noqa: BLE001
        if not ARM_JSON_FILE.exists():
            raise RuntimeError(f"Unable to compile Bicep and no prebuilt ARM JSON found: {exc}") from exc
        print(f"[warn] bicep build failed ({exc}); using existing {ARM_JSON_FILE.name}")
    return json.loads(ARM_JSON_FILE.read_text(encoding="utf-8"))


def ensure_resource_group(sub: str, rg: str, region: str, tags: dict) -> None:
    resp = arm(
        "PUT",
        f"/subscriptions/{sub}/resourcegroups/{rg}",
        params={"api-version": RG_API},
        body={"location": region, "tags": tags},
    )
    if resp.status_code not in (200, 201):
        raise RuntimeError(f"Failed to create resource group {rg}: {resp.status_code} {resp.text[:600]}")


def _paged(url: str) -> list[dict]:
    """GET an ARM collection, following nextLink until exhausted."""
    out: list[dict] = []
    params: dict | None = {"api-version": COGSVC_API}
    while url:
        resp = arm("GET", url, params=params)
        if resp.status_code != 200:
            break
        data = resp.json()
        out.extend(data.get("value", []))
        url = data.get("nextLink")
        params = None
    return out


def list_accounts(sub: str, region: str | None = None) -> list[dict]:
    out = _paged(f"/subscriptions/{sub}/providers/Microsoft.CognitiveServices/accounts")
    if region:
        out = [a for a in out if (a.get("location") or "").lower() == region.lower()]
    return out


def get_usages(sub: str, region: str) -> list[dict]:
    return _paged(
        f"/subscriptions/{sub}/providers/Microsoft.CognitiveServices/locations/{region}/usages"
    )


def list_region_models(sub: str, region: str) -> list[dict]:
    return _paged(
        f"/subscriptions/{sub}/providers/Microsoft.CognitiveServices/locations/{region}/models"
    )


def deploy_account(
    sub: str,
    rg: str,
    region: str,
    template: dict,
    account_name: str,
    index: int,
    models: list[dict],
    deploy_models: bool,
    deploy_project: bool,
    deployment_sku: str,
    tags: dict,
    poll_interval: int = 15,
    timeout_s: int = 2400,
) -> AttemptResult:
    """Run a single RG-scoped ARM deployment and wait for a terminal state."""
    dep_name = f"fdy-{index:03d}-{int(time.time())}"
    res = AttemptResult(
        index=index,
        account_name=account_name,
        deployment_name=dep_name,
        started_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
    )
    t0 = time.time()

    parameters = {
        "accountName": {"value": account_name},
        "location": {"value": region},
        "projectName": {"value": "proj-default"},
        "modelDeployments": {"value": models},
        "deploymentSku": {"value": deployment_sku},
        "deployModels": {"value": deploy_models},
        "deployProject": {"value": deploy_project},
        "tags": {"value": tags},
    }
    body = {"properties": {"mode": "Incremental", "template": template, "parameters": parameters}}
    url = (
        f"/subscriptions/{sub}/resourcegroups/{rg}"
        f"/providers/Microsoft.Resources/deployments/{dep_name}"
    )

    try:
        resp = arm("PUT", url, params={"api-version": DEPLOYMENTS_API}, body=body)
        if resp.status_code not in (200, 201):
            code, msg = flatten_error(resp.json().get("error", {})) if resp.text else ("", resp.text)
            res.status, res.error_code, res.error_message = "Error", code or str(resp.status_code), msg
            res.classification = classify(f"{code} {msg}", account_name)
            res.duration_s = round(time.time() - t0, 1)
            res.finished_utc = dt.datetime.now(dt.timezone.utc).isoformat()
            return res

        # Poll to terminal state.
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            time.sleep(poll_interval)
            g = arm("GET", url, params={"api-version": DEPLOYMENTS_API})
            if g.status_code != 200:
                continue
            props = g.json().get("properties", {})
            state = props.get("provisioningState", "Running")
            if state in ("Succeeded", "Failed", "Canceled"):
                res.status = state
                if state == "Succeeded":
                    res.classification = "ok"
                    outs = props.get("outputs") or {}
                    res.endpoint = (outs.get("endpoint") or {}).get("value", "")
                    res.provisioned_models = (outs.get("deployedModels") or {}).get("value", []) or []
                else:
                    code, msg = flatten_error(props.get("error", {}))
                    res.error_code, res.error_message = code, msg
                    res.classification = classify(f"{code} {msg}", account_name)
                break
        else:
            res.status, res.classification = "Timeout", "transient"
            res.error_message = f"Deployment did not reach a terminal state within {timeout_s}s"
    except Exception as exc:  # noqa: BLE001
        res.status = "Error"
        res.error_message = f"{type(exc).__name__}: {exc}"[:2000]
        res.classification = classify(res.error_message, account_name)

    res.duration_s = round(time.time() - t0, 1)
    res.finished_utc = dt.datetime.now(dt.timezone.utc).isoformat()
    return res


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------
def write_reports(results_dir: pathlib.Path, payload: dict) -> tuple[pathlib.Path, pathlib.Path]:
    results_dir.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    region = payload["run"]["region"]
    json_path = results_dir / f"foundry-limit-{region}-{stamp}.json"
    md_path = results_dir / f"foundry-limit-{region}-{stamp}.md"

    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    run, summary = payload["run"], payload["summary"]
    attempts = payload["attempts"]

    lines: list[str] = []
    lines.append(f"# Foundry account limit test - {region}\n")
    lines.append(f"**Run (UTC):** {run['started_utc']} -> {run['finished_utc']}  ")
    lines.append(f"**Subscription:** `{run['subscription_id']}`  ")
    lines.append(f"**Tenant:** `{run['tenant_id']}`  ")
    lines.append(f"**Resource group:** `{run['resource_group']}`  ")
    lines.append(f"**Region:** `{region}`  ")
    lines.append(f"**Mode:** basic agent setup (Microsoft-managed agent storage)  ")
    lines.append(f"**Deployment SKU:** `{run['deployment_sku']}`  ")
    lines.append(f"**Models per account:** {', '.join(run['models']) or '(none - account/project only)'}  ")
    lines.append(f"**Parallelism:** {run['parallel']}  \n")

    lines.append("## Result summary\n")
    lines.append("| Metric | Value |")
    lines.append("| --- | --- |")
    lines.append(f"| Pre-existing Foundry accounts in region | {summary['preexisting_accounts']} |")
    lines.append(f"| Accounts attempted this run | {summary['attempted']} |")
    lines.append(f"| Accounts created successfully | **{summary['succeeded']}** |")
    lines.append(f"| Total accounts now in region | **{summary['total_in_region_after']}** |")
    lines.append(f"| Failures - account-count cap | {summary['failed_account_cap']} |")
    lines.append(f"| Failures - model quota | {summary['failed_model_quota']} |")
    lines.append(f"| Failures - capacity | {summary['failed_capacity']} |")
    lines.append(f"| Failures - transient | {summary['failed_transient']} |")
    lines.append(f"| Failures - other | {summary['failed_other']} |")
    lines.append(f"| Model deployments created | {summary['model_deployments_created']} |")
    lines.append(f"| Mean deployment duration (s) | {summary['mean_duration_s']} |")
    lines.append(f"| Wall-clock duration (s) | {summary['wall_clock_s']} |")
    lines.append(f"| Documented cap (Foundry resources/region/sub) | {summary['documented_cap']} |")
    lines.append(f"| Cap reached in this run? | {'YES' if summary['cap_reached'] else 'no'} |\n")

    lines.append("## Verdict\n")
    lines.append(summary["verdict"] + "\n")

    if payload.get("quota"):
        lines.append("## Regional model quota at start of run\n")
        lines.append("| Quota | Used | Limit | Headroom |")
        lines.append("| --- | ---: | ---: | ---: |")
        for q in payload["quota"]:
            lines.append(f"| `{q['name']}` | {q['current']:g} | {q['limit']:g} | {q['limit'] - q['current']:g} |")
        lines.append("")

    failures = [a for a in attempts if a["classification"] not in ("ok",)]
    if failures:
        lines.append("## Failures\n")
        lines.append("| # | Account | Class | Code | Message |")
        lines.append("| ---: | --- | --- | --- | --- |")
        for a in failures[:60]:
            msg = (a["error_message"] or "").replace("\n", " ").replace("|", "\\|")[:220]
            lines.append(f"| {a['index']} | `{a['account_name']}` | {a['classification']} | `{a['error_code']}` | {msg} |")
        lines.append("")

    lines.append("## All attempts\n")
    lines.append("| # | Account | Status | Class | Duration (s) | Models |")
    lines.append("| ---: | --- | --- | --- | ---: | ---: |")
    for a in attempts:
        lines.append(
            f"| {a['index']} | `{a['account_name']}` | {a['status']} | {a['classification']} "
            f"| {a['duration_s']} | {len(a['provisioned_models'])} |"
        )
    lines.append("")

    md_path.write_text("\n".join(lines), encoding="utf-8")
    return json_path, md_path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
DEFAULT_MODELS = [
    {"name": "gpt-5.6-sol", "model": "gpt-5.6-sol", "version": "2026-07-09", "capacity": 1},
    {"name": "gpt-5.4", "model": "gpt-5.4", "version": "2026-03-05", "capacity": 1},
    {"name": "gpt-5.4-nano", "model": "gpt-5.4-nano", "version": "2026-03-17", "capacity": 1},
    {"name": "text-embedding-3-large", "model": "text-embedding-3-large", "version": "1", "capacity": 1},
]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--subscription", default=os.getenv("AZURE_SUBSCRIPTION_ID"), required=False)
    p.add_argument("--tenant", default=os.getenv("AZURE_TENANT_ID"))
    p.add_argument("--region", default="swedencentral")
    p.add_argument("--resource-group", default=None, help="Defaults to rg-foundry-limit-<region>")
    p.add_argument("--target", type=int, default=100, help="Number of accounts to attempt")
    p.add_argument("--parallel", type=int, default=8, help="Concurrent ARM deployments")
    p.add_argument("--prefix", default=None, help="Account-name prefix (default fdy<region-abbrev>)")
    p.add_argument("--capacity", type=int, default=1, help="Capacity units per model deployment")
    p.add_argument("--deployment-sku", default="GlobalStandard",
                   choices=["GlobalStandard", "DataZoneStandard", "Standard"])
    p.add_argument("--no-models", action="store_true", help="Account+project only (fast cap probe)")
    p.add_argument("--no-project", action="store_true", help="Account only")
    p.add_argument("--models-json", default=None, help="Path to a JSON array overriding the model list")
    p.add_argument("--stop-after-cap-hits", type=int, default=3,
                   help="Stop scheduling new work after this many account-cap failures")
    p.add_argument("--results-dir", default=str(REPO_ROOT / "results"))
    p.add_argument("--start-index", type=int, default=1)
    p.add_argument("--dry-run", action="store_true", help="Preflight only; deploy nothing")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    global TOKENS
    args = parse_args(argv)

    if not args.subscription:
        print("ERROR: --subscription (or AZURE_SUBSCRIPTION_ID) is required.", file=sys.stderr)
        return 2

    region = args.region.lower().replace(" ", "")
    rg = args.resource_group or f"rg-foundry-limit-{region}"
    prefix = args.prefix or f"fdy{region[:3]}"
    results_dir = pathlib.Path(args.results_dir)

    models = json.loads(pathlib.Path(args.models_json).read_text(encoding="utf-8")) if args.models_json else [
        dict(m) for m in DEFAULT_MODELS
    ]
    for m in models:
        m["capacity"] = args.capacity

    TOKENS = TokenProvider(args.tenant)
    run_id = "".join(random.choices(string.ascii_lowercase + string.digits, k=5))
    tags = {
        "purpose": "foundry-account-limit-test",
        "mode": "basic-agent-setup",
        "runId": run_id,
        "createdBy": "foundry_limit_test.py",
    }

    print("=" * 78)
    print(f"Foundry account limit test | region={region} | rg={rg} | target={args.target}")
    print("=" * 78)

    # ---------------- Preflight ----------------
    existing = list_accounts(args.subscription, region)
    foundry_existing = [a for a in existing if (a.get("kind") or "") == "AIServices"]
    print(f"[preflight] Cognitive Services accounts already in {region}: {len(existing)} "
          f"(AIServices/Foundry: {len(foundry_existing)})")

    quota_rows = []
    wanted = {m["model"].lower() for m in models}
    for u in get_usages(args.subscription, region):
        name = (u.get("name") or {}).get("value", "")
        if args.deployment_sku in name and any(w in name.lower() for w in wanted):
            quota_rows.append({
                "name": name,
                "current": float(u.get("currentValue") or 0),
                "limit": float(u.get("limit") or 0),
            })
    for q in sorted(quota_rows, key=lambda r: r["name"]):
        print(f"[preflight] quota {q['name']}: {q['current']:g}/{q['limit']:g}")

    if not args.no_models:
        catalog = list_region_models(args.subscription, region)
        available = {}
        for entry in catalog:
            mdl = entry.get("model") or {}
            key = (mdl.get("name", "").lower(), str(mdl.get("version", "")))
            available[key] = {s.get("name") for s in (mdl.get("skus") or [])}
        missing = []
        for m in models:
            key = (m["model"].lower(), str(m["version"]))
            skus = available.get(key)
            if skus is None:
                missing.append(f"{m['model']}:{m['version']} not offered in {region}")
            elif args.deployment_sku not in skus:
                missing.append(f"{m['model']}:{m['version']} has no {args.deployment_sku} SKU in {region}")
        if missing:
            print("[preflight] MODEL AVAILABILITY PROBLEMS:")
            for x in missing:
                print(f"           - {x}")
            return 3
        print(f"[preflight] all {len(models)} models available in {region} with {args.deployment_sku}")

    # Effective headroom against the documented cap.
    documented_cap = 100
    headroom = documented_cap - len(foundry_existing)
    print(f"[preflight] documented cap = {documented_cap} Foundry resources/region/subscription; "
          f"headroom = {headroom}")

    if args.dry_run:
        print("[dry-run] preflight complete; nothing deployed.")
        return 0

    template = build_template()
    ensure_resource_group(args.subscription, rg, region, tags)
    print(f"[setup] resource group ready: {rg}")

    # ---------------- Fan out ----------------
    started = dt.datetime.now(dt.timezone.utc)
    t_start = time.time()
    results: list[AttemptResult] = []
    cap_hits = 0
    stop_flag = threading.Event()
    lock = threading.Lock()
    done = 0

    indices = list(range(args.start_index, args.start_index + args.target))

    def work(i: int) -> AttemptResult | None:
        if stop_flag.is_set():
            return None
        name = f"{prefix}-{run_id}-{i:03d}"
        return deploy_account(
            args.subscription, rg, region, template, name, i, models,
            deploy_models=not args.no_models,
            deploy_project=not args.no_project,
            deployment_sku=args.deployment_sku,
            tags=tags,
        )

    with ThreadPoolExecutor(max_workers=args.parallel) as pool:
        futures = {pool.submit(work, i): i for i in indices}
        for fut in as_completed(futures):
            r = fut.result()
            if r is None:
                continue
            with lock:
                results.append(r)
                done += 1
                if r.classification == "account-cap":
                    cap_hits += 1
                    if cap_hits >= args.stop_after_cap_hits:
                        stop_flag.set()
                ok = sum(1 for x in results if x.classification == "ok")
                flag = "OK " if r.classification == "ok" else "FAIL"
                print(f"[{done}/{len(indices)}] {flag} #{r.index} {r.account_name} "
                      f"({r.status}/{r.classification}, {r.duration_s}s) | cumulative OK={ok}")

    wall = round(time.time() - t_start, 1)
    finished = dt.datetime.now(dt.timezone.utc)
    results.sort(key=lambda r: r.index)

    # ---------------- Summarize ----------------
    after = [a for a in list_accounts(args.subscription, region) if (a.get("kind") or "") == "AIServices"]
    succeeded = sum(1 for r in results if r.classification == "ok")
    by_class = {c: sum(1 for r in results if r.classification == c)
                for c in ("account-cap", "model-quota", "capacity", "transient", "other")}
    durations = [r.duration_s for r in results if r.classification == "ok"]
    cap_reached = by_class["account-cap"] > 0

    if cap_reached:
        verdict = (
            f"**Hard account cap reached.** {len(after)} Foundry (AIServices) accounts exist in "
            f"`{region}`; further account creations were rejected by the platform with an "
            f"account-count error. This confirms the documented limit of {documented_cap} "
            f"Foundry resources per region per subscription."
        )
    elif by_class["model-quota"] > 0:
        verdict = (
            f"**Model-capacity quota reached before the account cap.** {succeeded} accounts were "
            f"created; further deployments failed on model TPM quota, not account count. Reduce "
            f"`--capacity`, drop models, or request a model quota increase to push to the account cap."
        )
    elif len(after) >= documented_cap:
        verdict = (
            f"**Documented cap reached exactly.** {len(after)} Foundry accounts now exist in `{region}`, "
            f"matching the documented limit of {documented_cap} per region per subscription."
        )
    else:
        verdict = (
            f"**Cap not reached.** {succeeded}/{len(results)} attempts succeeded and "
            f"{len(after)} Foundry accounts now exist in `{region}`, below the documented cap of "
            f"{documented_cap}. Re-run with a higher `--target` to push further."
        )

    payload = {
        "run": {
            "started_utc": started.isoformat(),
            "finished_utc": finished.isoformat(),
            "subscription_id": args.subscription,
            "tenant_id": args.tenant or "(cli default)",
            "resource_group": rg,
            "region": region,
            "run_id": run_id,
            "target": args.target,
            "parallel": args.parallel,
            "deployment_sku": args.deployment_sku,
            "capacity_per_deployment": args.capacity,
            "deploy_models": not args.no_models,
            "deploy_project": not args.no_project,
            "models": [] if args.no_models else [m["name"] for m in models],
        },
        "summary": {
            "preexisting_accounts": len(foundry_existing),
            "attempted": len(results),
            "succeeded": succeeded,
            "total_in_region_after": len(after),
            "failed_account_cap": by_class["account-cap"],
            "failed_model_quota": by_class["model-quota"],
            "failed_capacity": by_class["capacity"],
            "failed_transient": by_class["transient"],
            "failed_other": by_class["other"],
            "model_deployments_created": sum(len(r.provisioned_models) for r in results),
            "mean_duration_s": round(sum(durations) / len(durations), 1) if durations else 0,
            "wall_clock_s": wall,
            "documented_cap": documented_cap,
            "cap_reached": cap_reached,
            "verdict": verdict,
        },
        "quota": sorted(quota_rows, key=lambda r: r["name"]),
        "attempts": [asdict(r) for r in results],
    }

    json_path, md_path = write_reports(results_dir, payload)

    print("\n" + "=" * 78)
    print(f"Succeeded          : {succeeded}/{len(results)}")
    print(f"Accounts in region : {len(after)} (cap {documented_cap})")
    print(f"Failure breakdown  : {by_class}")
    print(f"Wall clock         : {wall}s")
    print(f"Verdict            : {re.sub(r'[*`]', '', verdict)}")
    print(f"Reports            : {json_path}")
    print(f"                     {md_path}")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
