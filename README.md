# Microsoft Foundry — Account Limit Test Harness

Empirically determines the **maximum number of Microsoft Foundry accounts in
"basic mode"** (basic agent setup) that can be deployed into a single Azure
subscription, in a single region, inside one resource group — and proves the
resulting accounts are actually usable.

**Documented limit: 100 Foundry resources per region, per Azure subscription.**
**Empirically confirmed: exactly 100.** ✅

A live run drove Sweden Central to 100 accounts (97 created + 3 pre-existing) and every
further attempt was rejected by the platform with an account-cap error. See
[`docs/foundry-account-limits.md`](docs/foundry-account-limits.md) for the full research
write-up with Microsoft Learn citations and the measured results.

### Result summary

| | |
|---|---|
| Region | Sweden Central |
| Cap reached at | **100 accounts** |
| Attempts made | 102 (deliberate overshoot) |
| Created / rejected | 97 created, 5 rejected as `account-cap` |
| Wall clock | 424.6 s at parallelism 10 |
| Per-account time | ~37–58 s (account + project) |
| Data-plane check | ✅ chat + embedding both returned over Entra ID auth |
| Resource group | not a constraint — all 100 coexisted in one group |

The platform reports the cap as `InsufficientQuota` /
`"Cannot create/update/move resource '<accountName>'"` — there is no message mentioning
"100" or "accounts", so the harness classifies it by detecting that the message names the
**account** rather than a model capacity figure.

---

## Layout

| Path | Purpose |
|---|---|
| `docs/foundry-account-limits.md` | The research document — every governing limit, its source, and the pitfalls |
| `infra/foundry-account.bicep` | Deployment unit: 1 Foundry account + 1 project + N Global Standard model deployments |
| `infra/foundry-account.json` | Compiled ARM template (regenerated at runtime) |
| `scripts/foundry_limit_test.py` | Orchestrator — preflight, parallel fan-out, failure classification, reporting |
| `scripts/cleanup.py` | Teardown — delete child projects, delete accounts, **and purge** (soft-delete keeps consuming quota) |
| `tests/test_dataplane.py` | Data-plane proof — real chat completion + embedding over Entra ID auth |
| `tests/test_classify.py` | Regression tests for failure classification, incl. replay of real recorded errors |
| `results/` | Timestamped JSON datasets and Markdown run reports |

---

## Target environment

| | |
|---|---|
| Tenant | `2bab7b85-25a5-40d1-a83e-77d201b4da49` |
| Subscription | `70356d4b-bebe-4358-8baa-5dbdaf412088` |
| Region | `swedencentral` (primary), `eastus2` (comparison) |
| Resource group | `rg-foundry-limit-swedencentral` |
| Deployment type | Global Standard |

Models under test:

| Model | Version |
|---|---|
| `gpt-5.6-sol` | `2026-07-09` |
| `gpt-5.4` | `2026-03-05` |
| `gpt-5.4-nano` | `2026-03-17` |
| `text-embedding-3-large` | `1` |

---

## Prerequisites

- Azure CLI ≥ 2.60 with the Bicep CLI (`az bicep install`)
- Python 3.9+ with `requests`, `azure-identity`, `openai`
- `Contributor` (or `Cognitive Services Contributor`) on the subscription
- `Cognitive Services OpenAI User` for the data-plane test
- `Microsoft.CognitiveServices` provider registered

```powershell
az login --tenant 2bab7b85-25a5-40d1-a83e-77d201b4da49
az account set --subscription 70356d4b-bebe-4358-8baa-5dbdaf412088
az provider register -n Microsoft.CognitiveServices
pip install requests azure-identity openai
```

---

## Usage

### 1. Preflight (no resources created)

Validates subscription access, provider registration, region support, model +
Global Standard availability, current quota, and computes remaining headroom.

```powershell
python scripts\foundry_limit_test.py `
  --subscription 70356d4b-bebe-4358-8baa-5dbdaf412088 `
  --tenant 2bab7b85-25a5-40d1-a83e-77d201b4da49 `
  --region swedencentral `
  --dry-run
```

### 2. Smoke test — 2 complete basic-mode environments

Account + project + all four Global Standard model deployments.

```powershell
python scripts\foundry_limit_test.py `
  --subscription 70356d4b-bebe-4358-8baa-5dbdaf412088 `
  --tenant 2bab7b85-25a5-40d1-a83e-77d201b4da49 `
  --region swedencentral `
  --resource-group rg-foundry-limit-swedencentral `
  --target 2 --parallel 2
```

### 3. Full cap probe — deliberately overshoot 100

Account + project only (`--no-models`) so that the **account count**, not model
capacity quota, is the binding constraint.

```powershell
python scripts\foundry_limit_test.py `
  --subscription 70356d4b-bebe-4358-8baa-5dbdaf412088 `
  --tenant 2bab7b85-25a5-40d1-a83e-77d201b4da49 `
  --region swedencentral `
  --resource-group rg-foundry-limit-swedencentral `
  --target 102 --parallel 10 --no-models --prefix fdycap
```

### 4. Prove the data plane works

```powershell
python tests\test_dataplane.py `
  -g rg-foundry-limit-swedencentral `
  --prefix fdyswe --max 2
```

### 5. Tear down (delete **and** purge)

```powershell
python scripts\cleanup.py `
  -g rg-foundry-limit-swedencentral `
  --region swedencentral `
  --prefix fdy --purge --delete-group
```

Two things make teardown non-obvious, and both are handled automatically:

- **Child projects block account deletion.** ARM returns `CannotDeleteResource`
  ("Cannot delete resource while nested resources exist") if you `DELETE` an account
  that still has a project. Basic-mode accounts always have `proj-default`, so the
  script deletes every child project and polls each to 404 before touching the account.
- **Soft-delete keeps consuming the cap.** A deleted Cognitive Services account is
  retained for 48 h and still occupies its slot in the 100. `--purge` is what actually
  frees the region. Deleting the resource group alone cascades the accounts away but
  leaves them all soft-deleted — the region stays full until you purge.

---

## Key flags — `foundry_limit_test.py`

| Flag | Default | Notes |
|---|---|---|
| `--region` | `swedencentral` | Also a 2,000-concurrent-agent-session region |
| `--target` | — | Accounts to attempt. Overshoot the cap to prove where it is |
| `--parallel` | `8` | Concurrent ARM deployments |
| `--capacity` | `1` | Units per model deployment. **Keep at 1** when measuring the account cap |
| `--no-models` | off | Skip model deployments — much faster cap probing |
| `--no-project` | off | Skip project creation — bare account probing |
| `--deployment-sku` | `GlobalStandard` | Also accepts `DataZoneStandard`, `Standard` |
| `--stop-after-cap-hits` | `3` | Consecutive `account-cap` failures before concluding |
| `--start-index` | `1` | Resume numbering after a partial run |
| `--dry-run` | off | Preflight only |

---

## How failures are classified

Only one bucket means "we found the limit":

| Bucket | Meaning | Confirms the cap? |
|---|---|---|
| `account-cap` | Regional Foundry / Cognitive Services account ceiling reached | ✅ **yes** |
| `model-quota` | Not enough model capacity (TPM) quota | ❌ raise quota or lower `--capacity` |
| `capacity` | Region/SKU temporarily out of capacity | ❌ retry or change region |
| `transient` | Throttling, 409 conflict, timeout | ❌ retried automatically |
| `other` | Unmatched — inspect manually | ❌ |

---

## Gotchas worth knowing

- **Soft delete.** Deleted Cognitive Services accounts are retained 48 hours and
  keep consuming the regional cap. Always `--purge`, or your next run silently
  starts with less headroom.
- **ARM pagination.** The `locations/{region}/models`, `usages`, and `accounts`
  endpoints page at **50 entries**. A single `GET` will make you believe models
  are unavailable in a region. Follow `nextLink`.
- **409 on concurrent writes** to the same account — model deployments use
  `@batchSize(1)`. Different accounts stay fully parallel.
- **`kind=AIServices` (limit 100) ≠ `kind=OpenAI` (limit 30).** Separate buckets.
- **`F0` is capped at one account per type per subscription** — scale tests must use `S0`.
- **`BCP081` warnings** on api-version `2026-07-01` are benign; Bicep just lacks
  local type definitions for the newest API.

---

## Raising the limit

Azure portal → **Help + support** → **Create a support request** → issue type
**Service and subscription limits (quotas)** → quota type **Cognitive Services /
Azure AI services**. Provide subscription, region, `kind=AIServices`, target count,
and justification. Model *capacity* quota is a separate request via the Foundry
portal's **Management center → Quota** page.
