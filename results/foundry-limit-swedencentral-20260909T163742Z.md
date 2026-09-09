# Foundry account limit test - swedencentral

**Run (UTC):** 2026-09-09T16:37:31.536556+00:00 -> 2026-09-09T16:37:39.023925+00:00  
**Subscription:** `70356d4b-bebe-4358-8baa-5dbdaf412088`  
**Tenant:** `2bab7b85-25a5-40d1-a83e-77d201b4da49`  
**Resource group:** `rg-foundry-limit-swedencentral`  
**Region:** `swedencentral`  
**Mode:** basic agent setup (Microsoft-managed agent storage)  
**Deployment SKU:** `GlobalStandard`  
**Models per account:** gpt-5.6-sol, gpt-5.4, gpt-5.4-nano, text-embedding-3-large  
**Parallelism:** 2  

## Result summary

| Metric | Value |
| --- | --- |
| Pre-existing Foundry accounts in region | 1 |
| Accounts attempted this run | 2 |
| Accounts created successfully | **0** |
| Total accounts now in region | **1** |
| Failures - account-count cap | 2 |
| Failures - model quota | 0 |
| Failures - capacity | 0 |
| Failures - transient | 0 |
| Failures - other | 0 |
| Model deployments created | 0 |
| Mean deployment duration (s) | 0 |
| Wall-clock duration (s) | 7.5 |
| Documented cap (Foundry resources/region/sub) | 100 |
| Cap reached in this run? | YES |

## Verdict

**Hard account cap reached.** 1 Foundry (AIServices) accounts exist in `swedencentral`; further account creations were rejected by the platform with an account-count error. This confirms the documented limit of 100 Foundry resources per region per subscription.

## Regional model quota at start of run

| Quota | Used | Limit | Headroom |
| --- | ---: | ---: | ---: |
| `OpenAI.GlobalStandard.gpt-5.4` | 2 | 1000 | 998 |
| `OpenAI.GlobalStandard.gpt-5.4-mini` | 0 | 1000 | 1000 |
| `OpenAI.GlobalStandard.gpt-5.4-nano` | 2 | 5000 | 4998 |
| `OpenAI.GlobalStandard.gpt-5.4-pro` | 0 | 160 | 160 |
| `OpenAI.GlobalStandard.gpt-5.6-sol` | 2 | 1000 | 998 |
| `OpenAI.GlobalStandard.text-embedding-3-large` | 2 | 1000 | 998 |

## Failures

| # | Account | Class | Code | Message |
| ---: | --- | --- | --- | --- |
| 1 | `fdysmk-v3q1b-001` | account-cap | `InvalidTemplateDeployment/InsufficientQuota` | The template deployment 'fdy-001-1788971851' is not valid according to the validation procedure. The following resource provider(s) - 'Microsoft.CognitiveServices/accounts (2026-07-01)' reported preflight validation erro |
| 2 | `fdysmk-v3q1b-002` | account-cap | `InvalidTemplateDeployment/InsufficientQuota` | The template deployment 'fdy-002-1788971851' is not valid according to the validation procedure. The following resource provider(s) - 'Microsoft.CognitiveServices/accounts (2026-07-01)' reported preflight validation erro |

## All attempts

| # | Account | Status | Class | Duration (s) | Models |
| ---: | --- | --- | --- | ---: | ---: |
| 1 | `fdysmk-v3q1b-001` | Error | account-cap | 4.1 | 0 |
| 2 | `fdysmk-v3q1b-002` | Error | account-cap | 7.5 | 0 |
