# Microsoft Foundry — Maximum Accounts per Subscription per Region (Basic Mode)

**Question:** How many Microsoft Foundry accounts configured in *basic mode* (basic agent
setup) can be deployed into a single Azure subscription, in a single region, inside one
resource group?

**Short answer:** **100 Foundry resources per region, per Azure subscription.** This is a
soft, quota-managed limit that can be raised via a support request. Projects and model
deployments live *inside* each account and are governed by their own separate limits
(250 projects per account, 32 model deployments per account).

> **✅ Empirically confirmed.** This was not merely read from documentation — it was
> measured. A live fan-out test drove Sweden Central to exactly **100** accounts and every
> further attempt was rejected by the platform. See [§ 2.6](#26-empirical-confirmation).

| | |
|---|---|
| Tenant | `2bab7b85-25a5-40d1-a83e-77d201b4da49` (Entra External) |
| Subscription | `70356d4b-bebe-4358-8baa-5dbdaf412088` |
| Primary region | **Sweden Central** |
| Comparison region | East US 2 |
| Deployment type | Global Standard |
| Models under test | `gpt-5.6-sol`, `gpt-5.4`, `gpt-5.4-nano`, `text-embedding-3-large` |

---

## 1. What "basic mode" actually means

Microsoft Foundry Agent Service supports two provisioning topologies. The distinction
matters because it changes *which* Azure resources you must create, and therefore which
quota ceilings you can hit.

### Basic setup (what this document tests)

- Agent state — threads, messages, files, and vector stores — is persisted in
  **Microsoft-managed, logically-separated storage**.
- **No** customer-owned Azure Storage account, **no** Azure AI Search, **no** Azure Cosmos DB.
- **No capability host** wiring and no BYO connection objects.
- This is the default when you create a Foundry project without configuring your own
  data resources.

The deployable unit is therefore small:

```
Microsoft.CognitiveServices/accounts            (kind = AIServices)
└── Microsoft.CognitiveServices/accounts/projects
    └── Microsoft.CognitiveServices/accounts/deployments   (model deployments)
```

### Standard setup (out of scope here)

Agent state is written to **your own** Azure Storage account, Azure AI Search service, and
Azure Cosmos DB for NoSQL account. It gives you data residency and network isolation
control, but multiplies the number of resources per agent environment — and each of those
services carries its own per-subscription quota that would become the binding constraint
long before you reached 100 Foundry accounts.

> Source: [Microsoft Foundry Agent Service — quotas, limits and region support](https://learn.microsoft.com/azure/foundry/agents/concepts/limits-quotas-regions)

Because basic mode has the smallest resource footprint, it is the configuration that lets
you get closest to the raw **Foundry account** ceiling — which is exactly what we want to
measure.

---

## 2. The governing limits

### 2.1 The headline number — 100 resources per region per subscription

From *Microsoft Foundry Models quotas and limits*, table **"Resource limits (per Azure
subscription, per region)"**:

| Limit | Value |
|---|---|
| **Microsoft Foundry resources per region, per Azure subscription** | **100** |
| Maximum projects per Foundry resource | 250 |
| Maximum model deployments per Foundry resource | 32 |

> Source: <https://learn.microsoft.com/azure/foundry/foundry-models/quotas-limits>

This is the number that caps our experiment. With 250 projects allowed per account and 32
deployments per account, a fully-packed subscription in one region could theoretically
hold `100 × 250 = 25,000` projects and `100 × 32 = 3,200` model deployments.

### 2.2 The underlying Azure AI Services caps

A Foundry account is physically a `Microsoft.CognitiveServices/accounts` resource with
`kind = AIServices`. The Cognitive Services resource provider imposes its own ceilings,
documented under *Azure subscription and service limits, quotas, and constraints*:

| Limit | Value |
|---|---|
| Total Azure AI services resources per region (all kinds combined) | **200** |
| Azure AI services resources per region **for a single kind** | **100** |
| Free-tier (`F0`) accounts per resource type, per subscription | **1** |

> Source: <https://learn.microsoft.com/azure/azure-resource-manager/management/azure-subscription-service-limits>

The "100 per single kind" figure is the same 100 quoted by the Foundry docs — the Foundry
limit is the Cognitive Services per-kind limit surfaced under a Foundry-specific name. The
200 figure is a *mixed-kind* ceiling: you could hold 100 `AIServices` accounts plus 100
accounts of other kinds (Speech, Vision, Language, …) in the same region.

Practical consequence: **only `S0` accounts scale.** You get exactly one `F0` account per
type per subscription, so any scale test must use the `S0` SKU, which is what
`infra/foundry-account.bicep` does.

### 2.3 The 30-resource limit is a *different* limit — do not conflate them

Azure OpenAI documentation states a limit of **30 Azure OpenAI resources per region per
subscription**. That applies to accounts created with `kind = OpenAI` — the legacy,
single-service Azure OpenAI resource type.

It does **not** apply to Foundry accounts, which are `kind = AIServices`. The two resource
kinds are counted in separate buckets. This is one of the most common sources of confusion
when planning Foundry capacity, so it is worth restating:

| Resource kind | ARM `kind` | Per-region per-subscription limit |
|---|---|---|
| Microsoft Foundry resource | `AIServices` | **100** |
| Azure OpenAI resource (legacy) | `OpenAI` | **30** |

Our Bicep deliberately sets `kind: 'AIServices'` with `allowProjectManagement: true`, which
is the Foundry-account shape and the one governed by the 100 limit.

### 2.4 Agent Service runtime limits (per subscription per region)

Even after the accounts exist, the *runtime* has its own ceilings. The most relevant one
for anybody planning a large agent fleet is concurrent hosted agent sessions:

| Region tier | Concurrent hosted agent sessions |
|---|---|
| Canada Central, **East US 2**, Japan East, North Central US, South Africa North, Southeast Asia, **Sweden Central** | **2,000** |
| All other supported regions | **1,000** |

Fixed per-agent / per-thread limits (not adjustable):

| Limit | Value |
|---|---|
| Files per agent / per thread | 10,000 |
| Maximum single file size | 512 MB |
| Total file storage per resource | 100 GB |
| Tokens per vector-store file | 2,000,000 |
| Messages per thread | 100,000 |
| Characters per message | 1,500,000 |
| Tools per agent | 128 |
| Versions per agent | 1,000 |

> Source: <https://learn.microsoft.com/azure/foundry/agents/concepts/limits-quotas-regions>

**Sweden Central sits in the 2,000-session tier**, which is one of the reasons it was
chosen as the primary region for this test — it is not just available, it is a
top-tier Agent Service region.

### 2.5 Model capacity quota — the *other* thing that can stop you

Account count and model capacity are independent constraints. Each model deployment
consumes capacity units (TPM-derived) from a regional quota pool:

| Model | Quota in Sweden Central | Quota in East US 2 |
|---|---|---|
| `gpt-5.4` | 1,000 | 1,000 |
| `gpt-5.4-nano` | 5,000 | 5,000 |
| `gpt-5.6-sol` | 1,000 | 1,000 |
| `text-embedding-3-large` | 1,000 | 1,000 |

At the default `--capacity 1` used by the test harness, 100 accounts × 4 models × 1 unit
consumes only 100 units of each pool — roughly 10% of the tightest quota. This is
deliberate: the experiment is designed so that the **account count**, not model quota, is
the binding constraint. If you raise `--capacity`, model quota will fail first and you will
measure the wrong limit.

#### Subscription-level quota pooling (post May 7, 2026)

Quota management changed after **May 7, 2026**. Global Standard deployments of the same
model and version now draw from a **single subscription-wide pool shared across all
regions**, rather than a separate per-region allocation. In the Foundry portal's Quota
page, the *Scope* column shows `Global` or `Data Zone` for pooled deployment types and a
region name for region-scoped ones.

Implication for this test: because all four models are deployed as **Global Standard**,
their capacity is drawn from the global pool. Deploying the same models in a second region
(East US 2) for comparison will consume the *same* pool, not a fresh one.

---

## 2.6 Empirical confirmation

The documented figure was validated by actually deploying against it. This section records
what the platform did, not what the docs say.

### Run parameters

| | |
|---|---|
| Region | Sweden Central |
| Resource group | `rg-foundry-limit-swedencentral` |
| Attempts | 102 (deliberate overshoot) |
| Parallelism | 10 concurrent ARM deployments |
| Payload per attempt | 1 account (`kind=AIServices`, `S0`) + 1 project, models skipped (`--no-models`) |
| Wall clock | 424.6 s |
| Report | `results/foundry-limit-swedencentral-20260909T131416Z.json` |

### Result

| Metric | Value |
|---|---|
| New accounts created | 97 |
| Pre-existing accounts | 3 |
| **Total accounts in region at stop** | **100** |
| Attempts 98–102 | **all failed — account cap** |
| Per-account provisioning time | ~37–58 s (account + project) |

The count landed on **exactly 100** and stopped dead. Attempt 98 was the last one to even
be admitted; 99 through 102 were rejected outright.

A follow-up single-attempt run against the now-full region gave the cleanest possible
signal — rejection in **6.0 s** with zero ambiguity:

```text
[preflight] Cognitive Services accounts already in swedencentral: 100 (AIServices/Foundry: 100)
[preflight] documented cap = 100 Foundry resources/region/subscription; headroom = 0
[1/1] FAIL #1 fdyfull-h3svq-001 (Error/account-cap, 6.0s)
Verdict : Hard account cap reached.
```

### The actual error the platform returns

This is worth recording precisely, because it is **not** what you would guess. There is no
`QuotaExceeded`, no `ResourceCountExceeded`, and no message mentioning "100" or "accounts".
The cap surfaces as a generic quota error that identifies itself only by **naming the
account resource**:

```text
code:    InsufficientQuota
message: Insufficient quota. Cannot create/update/move resource '<accountName>'.
```

It arrives inside one of two envelopes depending on *when* the request lost:

| Envelope | When | Latency | Seen on |
|---|---|---|---|
| `InvalidTemplateDeployment` / `InsufficientQuota` | Rejected at ARM **preflight validation** — the cap was already full when the request arrived | ~3–6 s | attempts 99–102 |
| `DeploymentFailed` / `InsufficientQuota` | Passed preflight while headroom still existed, then **lost the race** at create time | ~21.7 s | attempt 98 |

That second envelope is a genuine race, and it is expected under parallel fan-out: with 10
in-flight requests, several can pass validation against the same last free slot and only one
can win. Any harness that treats a preflight-shaped error as the only cap signal will
misreport the boundary.

### Classification caveat

Because the cap error says only `InsufficientQuota`, it is **textually identical in its error
code** to a model-capacity quota failure. Distinguishing them requires reading what the
message names:

- **Account cap** → names the *account* (`Cannot create/update/move resource 'fdycap-…-098'`).
- **Model quota** → names a capacity figure, a SKU, a TPM value, or a model deployment.

Naively keying on the word "deployment" near "quota" does **not** work: ARM's generic
wrapper reads *"At least one resource **deployment** operation failed … | Insufficient
**quota**"* on account-cap failures too. The harness's `classify()` therefore matches on
specific capacity language (`capacity of quota`, `TPM`, `requested N … available M`,
`accounts/deployments`) and falls back to account-cap when the message names the account.
All five observed failures classify correctly as `account-cap` under this rule.

---


Verified live against the target subscription via the ARM
`locations/{region}/models` endpoint. All four models are offered with the
**GlobalStandard** SKU in both candidate regions:

| Model | Version | Sweden Central | East US 2 |
|---|---|---|---|
| `gpt-5.6-sol` | `2026-07-09` | ✅ GlobalStandard | ✅ GlobalStandard |
| `gpt-5.4` | `2026-03-05` | ✅ GlobalStandard | ✅ GlobalStandard |
| `gpt-5.4-nano` | `2026-03-17` | ✅ GlobalStandard | ✅ GlobalStandard |
| `text-embedding-3-large` | `1` | ✅ GlobalStandard | ✅ GlobalStandard |

> ⚠️ **API pagination gotcha.** The ARM models endpoint returns **50 entries per page**
> with a `nextLink`. A naive single `GET` sees only the first page and will incorrectly
> report models as "not available in this region". The harness follows `nextLink` in
> `_paged()`; any script you write against this endpoint must do the same.

### Provider registration

`Microsoft.CognitiveServices` must be `Registered` on the subscription:

```powershell
az provider show -n Microsoft.CognitiveServices --query registrationState -o tsv
# Registered
```

---

## 4. Practical ceiling in this subscription

The 100 limit counts **all** `AIServices` accounts already present in the region, not just
the ones this test creates.

| Item | Sweden Central |
|---|---|
| Documented cap | 100 |
| Pre-existing accounts (`admin-0849-resource`) | 1 |
| Smoke-test accounts (`fdyswe-q5y95-001/002`) | 2 |
| **Headroom at start of cap probe** | **97** |
| Accounts created by cap probe | 97 |
| **Observed ceiling** | **100 — confirmed, region full** |

Anyone reproducing this must subtract their own pre-existing accounts. The harness does
this automatically in preflight and prints the computed headroom. In this run the computed
headroom of 97 matched the number of accounts actually created **exactly**, which is the
strongest available evidence that the cap counts every `AIServices` account in the region
regardless of who created it or how.

### Soft-deleted accounts still count

Cognitive Services accounts **soft-delete**. A deleted account is retained for 48 hours and
continues to occupy a slot against the regional cap until it is purged. If you run this
test repeatedly you *will* exhaust the cap with invisible ghosts unless you purge:

```powershell
az cognitiveservices account purge -n <name> -g <rg> -l swedencentral
```

`scripts/cleanup.py` handles delete-then-purge automatically.

---

## 5. Raising the limit

The 100-resource cap is adjustable. To request an increase:

1. Azure portal → **Help + support** → **Create a support request**.
2. Issue type: **Service and subscription limits (quotas)**.
3. Quota type: **Cognitive Services** / **Azure AI services**.
4. Specify subscription, region, resource kind (`AIServices`), and the target count with a
   business justification.

Model *capacity* quota (TPM) is requested separately, either through the Foundry portal's
**Management center → Quota** page (which offers an inline "Request quota" action) or via
the same support-request flow with quota type **Azure OpenAI / Foundry Models**.

---

## 6. How the limit was tested

### 6.1 Deployment unit — `infra/foundry-account.bicep`

One Bicep module = one complete basic-mode Foundry environment:

| Resource | Configuration |
|---|---|
| `Microsoft.CognitiveServices/accounts` | `kind: AIServices`, `sku: S0`, `identity: SystemAssigned`, `allowProjectManagement: true`, `customSubDomainName: <accountName>` |
| `…/accounts/projects` | `proj-default` — basic setup, no capability host, no BYO connections |
| `…/accounts/deployments` | one per model, `sku.name: GlobalStandard`, `sku.capacity: 1` |

Two details worth calling out:

- **`allowProjectManagement: true`** is what makes the account a *Foundry* account rather
  than a plain Azure AI Services account. Without it you cannot create projects.
- **`@batchSize(1)`** on the model-deployment loop. Concurrent writes to the same Cognitive
  Services account return **409 Conflict**, so deployments within one account must be
  serialized. Different accounts remain fully parallel.

Toggles `deployModels` and `deployProject` allow a fast account-only probe when the goal is
purely to find the account ceiling.

### 6.2 Orchestrator — `scripts/foundry_limit_test.py`

```
preflight → create RG → parallel fan-out → classify failures → report
```

- Talks to **ARM REST directly** (`PUT …/providers/Microsoft.Resources/deployments/{name}`,
  api-version `2021-04-01`) rather than shelling out to `az deployment group create` per
  account. This is dramatically faster and yields structured error objects instead of
  scraped CLI text.
- Authenticates with `AzureCliCredential(tenant_id=…)` so it works even when the CLI is
  signed into multiple tenants. Tokens are cached thread-safely with a 5-minute pre-expiry
  refresh.
- Retries on `429` and `5xx`, honouring `Retry-After`.
- **Classifies every failure** into one of five buckets:

  | Bucket | Meaning | Counts as "found the limit"? |
  |---|---|---|
  | `account-cap` | Regional Foundry/Cognitive Services account ceiling reached | ✅ **yes** |
  | `model-quota` | Insufficient model capacity (TPM) quota | ❌ no — raise quota or lower `--capacity` |
  | `capacity` | Region/SKU temporarily out of capacity | ❌ no — retry or change region |
  | `transient` | Throttling, conflict, timeout | ❌ no — retried |
  | `other` | Unmatched | ❌ no — inspect manually |

  Only `account-cap` stops the run; after `--stop-after-cap-hits` consecutive cap failures
  the harness concludes the ceiling has been confirmed.

### 6.3 Reproducing

```powershell
az login --tenant 2bab7b85-25a5-40d1-a83e-77d201b4da49
az account set --subscription 70356d4b-bebe-4358-8baa-5dbdaf412088

# 1. Preflight only — no resources created
python scripts\foundry_limit_test.py `
  --subscription 70356d4b-bebe-4358-8baa-5dbdaf412088 `
  --tenant 2bab7b85-25a5-40d1-a83e-77d201b4da49 `
  --region swedencentral --dry-run

# 2. Smoke test — 2 full accounts incl. project + 4 model deployments
python scripts\foundry_limit_test.py ... --target 2 --parallel 2

# 3. Full cap probe — account + project only, deliberately overshoots 100
python scripts\foundry_limit_test.py ... --target 102 --parallel 10 --no-models

# 4. Prove the deployments are usable (data plane)
python tests\test_dataplane.py --account fdyswe-q5y95-001 -g rg-foundry-limit-swedencentral

# 5. Tear down and purge
python scripts\cleanup.py -g rg-foundry-limit-swedencentral --region swedencentral --purge
```

Results are written to `results/` as a timestamped JSON dataset plus a Markdown report.

---

## 7. Design notes and pitfalls

| Pitfall | Mitigation |
|---|---|
| ARM models/usages/accounts endpoints paginate at 50 | Follow `nextLink`; clear query params after the first hop because `nextLink` already embeds `api-version` |
| Parallel writes to one account → 409 | `@batchSize(1)` on the deployment loop |
| **Accounts cannot be deleted while child projects exist** → `CannotDeleteResource` | Delete every `accounts/{name}/projects/{project}` first, poll each to 404, *then* delete the account. Basic-mode accounts always have `proj-default`, so this is mandatory. `scripts/cleanup.py` does it automatically |
| Soft-deleted accounts still consume the cap for 48 h | Delete **and** purge between runs |
| `F0` is limited to one account per type | Use `S0` for any scale test |
| Bicep emits `BCP081` on api-version `2026-07-01` | Benign — Bicep simply lacks local type definitions for the newest API; deployment succeeds |
| `BCP138` — for-expressions are illegal in `output` | Use `map(modelDeployments, m => m.name)` instead of `[for m in …]` |
| Raising `--capacity` makes model quota fail before the account cap | Keep `--capacity 1` when measuring the account ceiling |
| Account cap and model quota share the `InsufficientQuota` code | Disambiguate on which resource the message names — see [§ 2.6](#26-empirical-confirmation). Covered by `tests/test_classify.py` |
| CLI logged into several tenants | Always pass `--tenant` explicitly |
| Deleting the resource group cascades, but leaves 99 soft-deleted accounts holding cap slots | Run the purge pass afterwards |

---

## 8. Summary of limits

| Limit | Value | Scope | Adjustable | Verified |
|---|---|---|---|---|
| **Foundry (`AIServices`) resources** | **100** | per region, per subscription | ✅ support request | **✅ measured** |
| Azure AI services resources, all kinds | 200 | per region, per subscription | ✅ | documented |
| Azure OpenAI (`kind=OpenAI`) resources | 30 | per region, per subscription | ✅ | documented |
| Free (`F0`) accounts | 1 | per type, per subscription | ❌ | documented |
| Projects | 250 | per Foundry resource | ❌ | documented |
| Model deployments | 32 | per Foundry resource | ❌ | documented |
| Concurrent hosted agent sessions | 2,000 (Sweden Central) / 1,000 elsewhere | per region, per subscription | ✅ | documented |
| Files per agent / thread | 10,000 | per agent / thread | ❌ | documented |
| Max file size | 512 MB | per file | ❌ | documented |
| Total file storage | 100 GB | per resource | ❌ | documented |
| Messages per thread | 100,000 | per thread | ❌ | documented |
| Tools per agent | 128 | per agent | ❌ | documented |

### Answer to the original question

> How many Foundry accounts in basic mode can be deployed in one subscription, one region,
> one resource group?

**100.** The resource group is not a constraint — it imposes no limit on Foundry account
count, and all 100 coexisted in a single group. The binding constraint is the
**per-region, per-subscription** cap of 100, which is adjustable via support request. Each
of those accounts can then hold up to 250 projects and 32 model deployments.


---

## 9. References

- [Microsoft Foundry Models — quotas and limits](https://learn.microsoft.com/azure/foundry/foundry-models/quotas-limits)
- [Foundry Agent Service — quotas, limits, and region support](https://learn.microsoft.com/azure/foundry/agents/concepts/limits-quotas-regions)
- [Azure subscription and service limits, quotas, and constraints](https://learn.microsoft.com/azure/azure-resource-manager/management/azure-subscription-service-limits)
- [Manage and increase quotas for Foundry resources](https://learn.microsoft.com/azure/ai-foundry/how-to/quota)
- [What is Microsoft Foundry Agent Service?](https://learn.microsoft.com/azure/foundry/agents/overview)
- [Foundry Models — deployment types (Global Standard)](https://learn.microsoft.com/azure/ai-foundry/concepts/deployment-types)
- [Cognitive Services account recovery / purge](https://learn.microsoft.com/azure/ai-services/recover-purge-resources)
