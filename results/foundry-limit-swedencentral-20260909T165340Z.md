# Foundry account limit test - swedencentral

**Run (UTC):** 2026-09-09T16:46:41.239984+00:00 -> 2026-09-09T16:53:33.248487+00:00  
**Subscription:** `70356d4b-bebe-4358-8baa-5dbdaf412088`  
**Tenant:** `2bab7b85-25a5-40d1-a83e-77d201b4da49`  
**Resource group:** `rg-foundry-limit-swedencentral`  
**Region:** `swedencentral`  
**Mode:** basic agent setup (Microsoft-managed agent storage)  
**Deployment SKU:** `GlobalStandard`  
**Models per account:** (none - account/project only)  
**Parallelism:** 10  

## Result summary

| Metric | Value |
| --- | --- |
| Pre-existing Foundry accounts in region | 3 |
| Accounts attempted this run | 102 |
| Accounts created successfully | **97** |
| Total accounts now in region | **100** |
| Failures - account-count cap | 5 |
| Failures - model quota | 0 |
| Failures - capacity | 0 |
| Failures - transient | 0 |
| Failures - other | 0 |
| Model deployments created | 0 |
| Mean deployment duration (s) | 40.7 |
| Wall-clock duration (s) | 412.0 |
| Documented cap (Foundry resources/region/sub) | 100 |
| Cap reached in this run? | YES |

## Verdict

**Hard account cap reached.** 100 Foundry (AIServices) accounts exist in `swedencentral`; further account creations were rejected by the platform with an account-count error. This confirms the documented limit of 100 Foundry resources per region per subscription.

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
| 98 | `fdycap2-6xsni-098` | account-cap | `DeploymentFailed/InsufficientQuota` | At least one resource deployment operation failed. Please list deployment operations for details. Please see https://aka.ms/arm-deployment-operations for usage details. \| Insufficient quota. Cannot create/update/move re |
| 99 | `fdycap2-6xsni-099` | account-cap | `DeploymentFailed/InsufficientQuota` | At least one resource deployment operation failed. Please list deployment operations for details. Please see https://aka.ms/arm-deployment-operations for usage details. \| Insufficient quota. Cannot create/update/move re |
| 100 | `fdycap2-6xsni-100` | account-cap | `InvalidTemplateDeployment/InsufficientQuota` | The template deployment 'fdy-100-1788972790' is not valid according to the validation procedure. The following resource provider(s) - 'Microsoft.CognitiveServices/accounts (2026-07-01)' reported preflight validation erro |
| 101 | `fdycap2-6xsni-101` | account-cap | `InvalidTemplateDeployment/InsufficientQuota` | The template deployment 'fdy-101-1788972790' is not valid according to the validation procedure. The following resource provider(s) - 'Microsoft.CognitiveServices/accounts (2026-07-01)' reported preflight validation erro |
| 102 | `fdycap2-6xsni-102` | account-cap | `InvalidTemplateDeployment/InsufficientQuota` | The template deployment 'fdy-102-1788972793' is not valid according to the validation procedure. The following resource provider(s) - 'Microsoft.CognitiveServices/accounts (2026-07-01)' reported preflight validation erro |

## All attempts

| # | Account | Status | Class | Duration (s) | Models |
| ---: | --- | --- | --- | ---: | ---: |
| 1 | `fdycap2-6xsni-001` | Succeeded | ok | 45.9 | 0 |
| 2 | `fdycap2-6xsni-002` | Succeeded | ok | 46.6 | 0 |
| 3 | `fdycap2-6xsni-003` | Succeeded | ok | 65.8 | 0 |
| 4 | `fdycap2-6xsni-004` | Succeeded | ok | 46.6 | 0 |
| 5 | `fdycap2-6xsni-005` | Succeeded | ok | 44.8 | 0 |
| 6 | `fdycap2-6xsni-006` | Succeeded | ok | 45.8 | 0 |
| 7 | `fdycap2-6xsni-007` | Succeeded | ok | 68.4 | 0 |
| 8 | `fdycap2-6xsni-008` | Succeeded | ok | 45.8 | 0 |
| 9 | `fdycap2-6xsni-009` | Succeeded | ok | 45.9 | 0 |
| 10 | `fdycap2-6xsni-010` | Succeeded | ok | 44.2 | 0 |
| 11 | `fdycap2-6xsni-011` | Succeeded | ok | 41.7 | 0 |
| 12 | `fdycap2-6xsni-012` | Succeeded | ok | 40.7 | 0 |
| 13 | `fdycap2-6xsni-013` | Succeeded | ok | 44.0 | 0 |
| 14 | `fdycap2-6xsni-014` | Succeeded | ok | 44.3 | 0 |
| 15 | `fdycap2-6xsni-015` | Succeeded | ok | 44.3 | 0 |
| 16 | `fdycap2-6xsni-016` | Succeeded | ok | 43.9 | 0 |
| 17 | `fdycap2-6xsni-017` | Succeeded | ok | 43.4 | 0 |
| 18 | `fdycap2-6xsni-018` | Succeeded | ok | 43.6 | 0 |
| 19 | `fdycap2-6xsni-019` | Succeeded | ok | 38.1 | 0 |
| 20 | `fdycap2-6xsni-020` | Succeeded | ok | 40.8 | 0 |
| 21 | `fdycap2-6xsni-021` | Succeeded | ok | 38.1 | 0 |
| 22 | `fdycap2-6xsni-022` | Succeeded | ok | 38.1 | 0 |
| 23 | `fdycap2-6xsni-023` | Succeeded | ok | 39.9 | 0 |
| 24 | `fdycap2-6xsni-024` | Succeeded | ok | 40.1 | 0 |
| 25 | `fdycap2-6xsni-025` | Succeeded | ok | 41.9 | 0 |
| 26 | `fdycap2-6xsni-026` | Succeeded | ok | 39.5 | 0 |
| 27 | `fdycap2-6xsni-027` | Succeeded | ok | 42.9 | 0 |
| 28 | `fdycap2-6xsni-028` | Succeeded | ok | 41.7 | 0 |
| 29 | `fdycap2-6xsni-029` | Succeeded | ok | 36.8 | 0 |
| 30 | `fdycap2-6xsni-030` | Succeeded | ok | 38.4 | 0 |
| 31 | `fdycap2-6xsni-031` | Succeeded | ok | 37.5 | 0 |
| 32 | `fdycap2-6xsni-032` | Succeeded | ok | 38.5 | 0 |
| 33 | `fdycap2-6xsni-033` | Succeeded | ok | 39.5 | 0 |
| 34 | `fdycap2-6xsni-034` | Succeeded | ok | 40.0 | 0 |
| 35 | `fdycap2-6xsni-035` | Succeeded | ok | 40.7 | 0 |
| 36 | `fdycap2-6xsni-036` | Succeeded | ok | 39.3 | 0 |
| 37 | `fdycap2-6xsni-037` | Succeeded | ok | 54.3 | 0 |
| 38 | `fdycap2-6xsni-038` | Succeeded | ok | 38.4 | 0 |
| 39 | `fdycap2-6xsni-039` | Succeeded | ok | 37.8 | 0 |
| 40 | `fdycap2-6xsni-040` | Succeeded | ok | 38.0 | 0 |
| 41 | `fdycap2-6xsni-041` | Succeeded | ok | 37.8 | 0 |
| 42 | `fdycap2-6xsni-042` | Succeeded | ok | 37.2 | 0 |
| 43 | `fdycap2-6xsni-043` | Succeeded | ok | 39.7 | 0 |
| 44 | `fdycap2-6xsni-044` | Succeeded | ok | 54.9 | 0 |
| 45 | `fdycap2-6xsni-045` | Succeeded | ok | 37.7 | 0 |
| 46 | `fdycap2-6xsni-046` | Succeeded | ok | 55.4 | 0 |
| 47 | `fdycap2-6xsni-047` | Succeeded | ok | 37.8 | 0 |
| 48 | `fdycap2-6xsni-048` | Succeeded | ok | 37.7 | 0 |
| 49 | `fdycap2-6xsni-049` | Succeeded | ok | 36.3 | 0 |
| 50 | `fdycap2-6xsni-050` | Succeeded | ok | 37.4 | 0 |
| 51 | `fdycap2-6xsni-051` | Succeeded | ok | 37.6 | 0 |
| 52 | `fdycap2-6xsni-052` | Succeeded | ok | 38.5 | 0 |
| 53 | `fdycap2-6xsni-053` | Succeeded | ok | 39.0 | 0 |
| 54 | `fdycap2-6xsni-054` | Succeeded | ok | 38.2 | 0 |
| 55 | `fdycap2-6xsni-055` | Succeeded | ok | 38.2 | 0 |
| 56 | `fdycap2-6xsni-056` | Succeeded | ok | 38.4 | 0 |
| 57 | `fdycap2-6xsni-057` | Succeeded | ok | 37.7 | 0 |
| 58 | `fdycap2-6xsni-058` | Succeeded | ok | 37.8 | 0 |
| 59 | `fdycap2-6xsni-059` | Succeeded | ok | 39.4 | 0 |
| 60 | `fdycap2-6xsni-060` | Succeeded | ok | 38.6 | 0 |
| 61 | `fdycap2-6xsni-061` | Succeeded | ok | 38.5 | 0 |
| 62 | `fdycap2-6xsni-062` | Succeeded | ok | 38.2 | 0 |
| 63 | `fdycap2-6xsni-063` | Succeeded | ok | 42.4 | 0 |
| 64 | `fdycap2-6xsni-064` | Succeeded | ok | 38.5 | 0 |
| 65 | `fdycap2-6xsni-065` | Succeeded | ok | 38.3 | 0 |
| 66 | `fdycap2-6xsni-066` | Succeeded | ok | 38.8 | 0 |
| 67 | `fdycap2-6xsni-067` | Succeeded | ok | 38.1 | 0 |
| 68 | `fdycap2-6xsni-068` | Succeeded | ok | 38.7 | 0 |
| 69 | `fdycap2-6xsni-069` | Succeeded | ok | 37.7 | 0 |
| 70 | `fdycap2-6xsni-070` | Succeeded | ok | 37.3 | 0 |
| 71 | `fdycap2-6xsni-071` | Succeeded | ok | 37.1 | 0 |
| 72 | `fdycap2-6xsni-072` | Succeeded | ok | 37.6 | 0 |
| 73 | `fdycap2-6xsni-073` | Succeeded | ok | 38.2 | 0 |
| 74 | `fdycap2-6xsni-074` | Succeeded | ok | 38.1 | 0 |
| 75 | `fdycap2-6xsni-075` | Succeeded | ok | 36.9 | 0 |
| 76 | `fdycap2-6xsni-076` | Succeeded | ok | 38.5 | 0 |
| 77 | `fdycap2-6xsni-077` | Succeeded | ok | 37.8 | 0 |
| 78 | `fdycap2-6xsni-078` | Succeeded | ok | 38.1 | 0 |
| 79 | `fdycap2-6xsni-079` | Succeeded | ok | 55.4 | 0 |
| 80 | `fdycap2-6xsni-080` | Succeeded | ok | 38.4 | 0 |
| 81 | `fdycap2-6xsni-081` | Succeeded | ok | 38.2 | 0 |
| 82 | `fdycap2-6xsni-082` | Succeeded | ok | 38.1 | 0 |
| 83 | `fdycap2-6xsni-083` | Succeeded | ok | 37.3 | 0 |
| 84 | `fdycap2-6xsni-084` | Succeeded | ok | 38.4 | 0 |
| 85 | `fdycap2-6xsni-085` | Succeeded | ok | 37.7 | 0 |
| 86 | `fdycap2-6xsni-086` | Succeeded | ok | 38.4 | 0 |
| 87 | `fdycap2-6xsni-087` | Succeeded | ok | 38.9 | 0 |
| 88 | `fdycap2-6xsni-088` | Succeeded | ok | 38.3 | 0 |
| 89 | `fdycap2-6xsni-089` | Succeeded | ok | 37.8 | 0 |
| 90 | `fdycap2-6xsni-090` | Succeeded | ok | 38.4 | 0 |
| 91 | `fdycap2-6xsni-091` | Succeeded | ok | 37.3 | 0 |
| 92 | `fdycap2-6xsni-092` | Succeeded | ok | 37.9 | 0 |
| 93 | `fdycap2-6xsni-093` | Succeeded | ok | 37.6 | 0 |
| 94 | `fdycap2-6xsni-094` | Succeeded | ok | 37.2 | 0 |
| 95 | `fdycap2-6xsni-095` | Succeeded | ok | 37.1 | 0 |
| 96 | `fdycap2-6xsni-096` | Succeeded | ok | 38.1 | 0 |
| 97 | `fdycap2-6xsni-097` | Succeeded | ok | 37.7 | 0 |
| 98 | `fdycap2-6xsni-098` | Failed | account-cap | 21.3 | 0 |
| 99 | `fdycap2-6xsni-099` | Failed | account-cap | 20.3 | 0 |
| 100 | `fdycap2-6xsni-100` | Error | account-cap | 3.1 | 0 |
| 101 | `fdycap2-6xsni-101` | Error | account-cap | 3.6 | 0 |
| 102 | `fdycap2-6xsni-102` | Error | account-cap | 3.7 | 0 |
