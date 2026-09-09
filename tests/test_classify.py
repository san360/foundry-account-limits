"""Regression tests for the failure classifier in ``foundry_limit_test``.

The account cap and model-capacity exhaustion share the ``InsufficientQuota``
error code, so ``classify()`` has to disambiguate them by reading which resource
the message names. That distinction is subtle and was got wrong once already:
an early version keyed on "deployment ... quota" being near each other, which
silently mislabelled real account-cap failures as model-quota because ARM's
generic wrapper reads "At least one resource *deployment* operation failed ...
| Insufficient *quota*".

The verbatim strings below were captured from a real run in swedencentral and
are the authoritative fixtures. Run with:

    python tests/test_classify.py
"""

from __future__ import annotations

import glob
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from foundry_limit_test import classify  # noqa: E402

# --------------------------------------------------------------------------
# Fixtures captured verbatim from real ARM responses.
# --------------------------------------------------------------------------

# Rejected at preflight validation once the region was already full.
CAP_PREFLIGHT = (
    "InvalidTemplateDeployment/InsufficientQuota The template deployment failed with "
    "error: 'The resource operation completed with terminal provisioning state "
    "'Failed'.' | Insufficient quota. Cannot create/update/move resource "
    "'fdycap-vhidn-099'."
)

# Passed preflight while headroom still existed, then lost the race at create
# time. Note the words "deployment" and "quota" both appear - this is the case
# that broke the naive classifier.
CAP_RACE = (
    "DeploymentFailed/InsufficientQuota At least one resource deployment operation "
    "failed. Please list deployment operations for details. Please see "
    "https://aka.ms/arm-deployment-operations for usage details. | Insufficient "
    "quota. Cannot create/update/move resource 'fdycap-vhidn-098'."
)

# Genuine model-capacity exhaustion - names a capacity figure and a SKU.
MODEL_CAPACITY = (
    "DeploymentFailed/InsufficientQuota Insufficient quota. Cannot create/update/move "
    "resource 'acct-1'. This deployment requires 500 capacity of quota SKU "
    "GlobalStandard, but only 10 available."
)

MODEL_TPM = (
    "InsufficientQuota The specified capacity '300' of account deployment is "
    "bigger than available capacity '82' for UsageName 'Tokens Per Minute (thousands) "
    "- gpt-5.4 GlobalStandard'."
)

CASES: list[tuple[str, str, str, str]] = [
    # (label, text, account_name, expected)
    ("cap - preflight envelope", CAP_PREFLIGHT, "fdycap-vhidn-099", "account-cap"),
    ("cap - create-time race", CAP_RACE, "fdycap-vhidn-098", "account-cap"),
    ("cap - no account name given", CAP_RACE, "", "account-cap"),
    ("model quota - capacity + SKU", MODEL_CAPACITY, "acct-1", "model-quota"),
    ("model quota - TPM usage name", MODEL_TPM, "acct-1", "model-quota"),
    ("explicit account count error", "SubscriptionResourceCountExceeded", "a", "account-cap"),
    ("max accounts wording", "Maximum number of accounts reached", "a", "account-cap"),
    ("throttling", "TooManyRequests 429 rate limited", "a", "transient"),
    ("concurrent write conflict", "Conflict another operation in progress", "a", "transient"),
    ("empty input", "", "a", "other"),
    ("unrelated failure", "AuthorizationFailed does not have permission", "a", "other"),
]


def run_unit_cases() -> int:
    failures = 0
    print("-- unit cases --")
    for label, text, account, expected in CASES:
        got = classify(text, account)
        ok = got == expected
        failures += 0 if ok else 1
        print(f"  [{'PASS' if ok else 'FAIL'}] {label:<32} expected={expected:<12} got={got}")
    return failures


def run_recorded_run() -> int:
    """Replay every failure from the most recent real run report."""
    reports = sorted(glob.glob(os.path.join(os.path.dirname(__file__), "..", "results", "*.json")))
    if not reports:
        print("\n-- recorded run: no reports found, skipping --")
        return 0

    failures = 0
    print("\n-- replay of recorded run failures --")
    for path in reports:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        bad = [a for a in data.get("attempts", []) if a.get("classification") != "ok"]
        if not bad:
            continue
        print(f"  {os.path.basename(path)}")
        for a in bad:
            got = classify(f"{a['error_code']} {a['error_message']}", a["account_name"])
            # Every failure in these runs was the account cap: the probe ran with
            # --no-models, so no model deployment existed to exhaust quota.
            ok = got == "account-cap"
            failures += 0 if ok else 1
            print(f"    [{'PASS' if ok else 'FAIL'}] {a['account_name']:<20} -> {got}")
    return failures


def main() -> int:
    failures = run_unit_cases() + run_recorded_run()
    print()
    if failures:
        print(f"FAILED - {failures} case(s) misclassified")
        return 1
    print("ALL PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
