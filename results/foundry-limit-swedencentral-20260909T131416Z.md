# Foundry account limit test - swedencentral

**Run (UTC):** 2026-09-09T13:04:33.636736+00:00 -> 2026-09-09T13:11:38.280893+00:00  
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
| Failures - account-count cap | 4 |
| Failures - model quota | 1 |
| Failures - capacity | 0 |
| Failures - transient | 0 |
| Failures - other | 0 |
| Model deployments created | 0 |
| Mean deployment duration (s) | 42.8 |
| Wall-clock duration (s) | 424.6 |
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
| 98 | `fdycap-vhidn-098` | model-quota | `DeploymentFailed/InsufficientQuota` | At least one resource deployment operation failed. Please list deployment operations for details. Please see https://aka.ms/arm-deployment-operations for usage details. \| Insufficient quota. Cannot create/update/move re |
| 99 | `fdycap-vhidn-099` | account-cap | `InvalidTemplateDeployment/InsufficientQuota` | The template deployment 'fdy-099-1788959472' is not valid according to the validation procedure. The following resource provider(s) - 'Microsoft.CognitiveServices/accounts (2026-07-01)' reported preflight validation erro |
| 100 | `fdycap-vhidn-100` | account-cap | `InvalidTemplateDeployment/InsufficientQuota` | The template deployment 'fdy-100-1788959474' is not valid according to the validation procedure. The following resource provider(s) - 'Microsoft.CognitiveServices/accounts (2026-07-01)' reported preflight validation erro |
| 101 | `fdycap-vhidn-101` | account-cap | `InvalidTemplateDeployment/InsufficientQuota` | The template deployment 'fdy-101-1788959478' is not valid according to the validation procedure. The following resource provider(s) - 'Microsoft.CognitiveServices/accounts (2026-07-01)' reported preflight validation erro |
| 102 | `fdycap-vhidn-102` | account-cap | `InvalidTemplateDeployment/InsufficientQuota` | The template deployment 'fdy-102-1788959479' is not valid according to the validation procedure. The following resource provider(s) - 'Microsoft.CognitiveServices/accounts (2026-07-01)' reported preflight validation erro |

## All attempts

| # | Account | Status | Class | Duration (s) | Models |
| ---: | --- | --- | --- | ---: | ---: |
| 1 | `fdycap-vhidn-001` | Succeeded | ok | 45.2 | 0 |
| 2 | `fdycap-vhidn-002` | Succeeded | ok | 50.0 | 0 |
| 3 | `fdycap-vhidn-003` | Succeeded | ok | 44.5 | 0 |
| 4 | `fdycap-vhidn-004` | Succeeded | ok | 48.0 | 0 |
| 5 | `fdycap-vhidn-005` | Succeeded | ok | 51.1 | 0 |
| 6 | `fdycap-vhidn-006` | Succeeded | ok | 51.5 | 0 |
| 7 | `fdycap-vhidn-007` | Succeeded | ok | 44.5 | 0 |
| 8 | `fdycap-vhidn-008` | Succeeded | ok | 50.6 | 0 |
| 9 | `fdycap-vhidn-009` | Succeeded | ok | 46.2 | 0 |
| 10 | `fdycap-vhidn-010` | Succeeded | ok | 50.2 | 0 |
| 11 | `fdycap-vhidn-011` | Succeeded | ok | 42.5 | 0 |
| 12 | `fdycap-vhidn-012` | Succeeded | ok | 41.7 | 0 |
| 13 | `fdycap-vhidn-013` | Succeeded | ok | 45.9 | 0 |
| 14 | `fdycap-vhidn-014` | Succeeded | ok | 44.2 | 0 |
| 15 | `fdycap-vhidn-015` | Succeeded | ok | 43.4 | 0 |
| 16 | `fdycap-vhidn-016` | Succeeded | ok | 42.1 | 0 |
| 17 | `fdycap-vhidn-017` | Succeeded | ok | 41.6 | 0 |
| 18 | `fdycap-vhidn-018` | Succeeded | ok | 41.7 | 0 |
| 19 | `fdycap-vhidn-019` | Succeeded | ok | 40.9 | 0 |
| 20 | `fdycap-vhidn-020` | Succeeded | ok | 63.4 | 0 |
| 21 | `fdycap-vhidn-021` | Succeeded | ok | 37.4 | 0 |
| 22 | `fdycap-vhidn-022` | Succeeded | ok | 38.9 | 0 |
| 23 | `fdycap-vhidn-023` | Succeeded | ok | 41.2 | 0 |
| 24 | `fdycap-vhidn-024` | Succeeded | ok | 54.6 | 0 |
| 25 | `fdycap-vhidn-025` | Succeeded | ok | 55.2 | 0 |
| 26 | `fdycap-vhidn-026` | Succeeded | ok | 40.3 | 0 |
| 27 | `fdycap-vhidn-027` | Succeeded | ok | 41.4 | 0 |
| 28 | `fdycap-vhidn-028` | Succeeded | ok | 42.0 | 0 |
| 29 | `fdycap-vhidn-029` | Succeeded | ok | 41.4 | 0 |
| 30 | `fdycap-vhidn-030` | Succeeded | ok | 39.1 | 0 |
| 31 | `fdycap-vhidn-031` | Succeeded | ok | 37.2 | 0 |
| 32 | `fdycap-vhidn-032` | Succeeded | ok | 38.2 | 0 |
| 33 | `fdycap-vhidn-033` | Succeeded | ok | 42.2 | 0 |
| 34 | `fdycap-vhidn-034` | Succeeded | ok | 39.3 | 0 |
| 35 | `fdycap-vhidn-035` | Succeeded | ok | 39.3 | 0 |
| 36 | `fdycap-vhidn-036` | Succeeded | ok | 39.1 | 0 |
| 37 | `fdycap-vhidn-037` | Succeeded | ok | 52.8 | 0 |
| 38 | `fdycap-vhidn-038` | Succeeded | ok | 37.9 | 0 |
| 39 | `fdycap-vhidn-039` | Succeeded | ok | 54.5 | 0 |
| 40 | `fdycap-vhidn-040` | Succeeded | ok | 40.8 | 0 |
| 41 | `fdycap-vhidn-041` | Succeeded | ok | 56.9 | 0 |
| 42 | `fdycap-vhidn-042` | Succeeded | ok | 38.6 | 0 |
| 43 | `fdycap-vhidn-043` | Succeeded | ok | 36.7 | 0 |
| 44 | `fdycap-vhidn-044` | Succeeded | ok | 38.6 | 0 |
| 45 | `fdycap-vhidn-045` | Succeeded | ok | 43.5 | 0 |
| 46 | `fdycap-vhidn-046` | Succeeded | ok | 43.3 | 0 |
| 47 | `fdycap-vhidn-047` | Succeeded | ok | 37.0 | 0 |
| 48 | `fdycap-vhidn-048` | Succeeded | ok | 36.9 | 0 |
| 49 | `fdycap-vhidn-049` | Succeeded | ok | 39.4 | 0 |
| 50 | `fdycap-vhidn-050` | Succeeded | ok | 57.3 | 0 |
| 51 | `fdycap-vhidn-051` | Succeeded | ok | 57.3 | 0 |
| 52 | `fdycap-vhidn-052` | Succeeded | ok | 39.8 | 0 |
| 53 | `fdycap-vhidn-053` | Succeeded | ok | 58.1 | 0 |
| 54 | `fdycap-vhidn-054` | Succeeded | ok | 38.3 | 0 |
| 55 | `fdycap-vhidn-055` | Succeeded | ok | 37.8 | 0 |
| 56 | `fdycap-vhidn-056` | Succeeded | ok | 39.3 | 0 |
| 57 | `fdycap-vhidn-057` | Succeeded | ok | 54.4 | 0 |
| 58 | `fdycap-vhidn-058` | Succeeded | ok | 38.8 | 0 |
| 59 | `fdycap-vhidn-059` | Succeeded | ok | 37.4 | 0 |
| 60 | `fdycap-vhidn-060` | Succeeded | ok | 39.2 | 0 |
| 61 | `fdycap-vhidn-061` | Succeeded | ok | 40.2 | 0 |
| 62 | `fdycap-vhidn-062` | Succeeded | ok | 40.7 | 0 |
| 63 | `fdycap-vhidn-063` | Succeeded | ok | 41.2 | 0 |
| 64 | `fdycap-vhidn-064` | Succeeded | ok | 40.8 | 0 |
| 65 | `fdycap-vhidn-065` | Succeeded | ok | 39.7 | 0 |
| 66 | `fdycap-vhidn-066` | Succeeded | ok | 37.5 | 0 |
| 67 | `fdycap-vhidn-067` | Succeeded | ok | 38.0 | 0 |
| 68 | `fdycap-vhidn-068` | Succeeded | ok | 36.9 | 0 |
| 69 | `fdycap-vhidn-069` | Succeeded | ok | 40.9 | 0 |
| 70 | `fdycap-vhidn-070` | Succeeded | ok | 38.7 | 0 |
| 71 | `fdycap-vhidn-071` | Succeeded | ok | 58.6 | 0 |
| 72 | `fdycap-vhidn-072` | Succeeded | ok | 41.0 | 0 |
| 73 | `fdycap-vhidn-073` | Succeeded | ok | 38.2 | 0 |
| 74 | `fdycap-vhidn-074` | Succeeded | ok | 41.0 | 0 |
| 75 | `fdycap-vhidn-075` | Succeeded | ok | 40.7 | 0 |
| 76 | `fdycap-vhidn-076` | Succeeded | ok | 38.2 | 0 |
| 77 | `fdycap-vhidn-077` | Succeeded | ok | 40.6 | 0 |
| 78 | `fdycap-vhidn-078` | Succeeded | ok | 39.2 | 0 |
| 79 | `fdycap-vhidn-079` | Succeeded | ok | 41.0 | 0 |
| 80 | `fdycap-vhidn-080` | Succeeded | ok | 41.4 | 0 |
| 81 | `fdycap-vhidn-081` | Succeeded | ok | 42.8 | 0 |
| 82 | `fdycap-vhidn-082` | Succeeded | ok | 42.8 | 0 |
| 83 | `fdycap-vhidn-083` | Succeeded | ok | 41.0 | 0 |
| 84 | `fdycap-vhidn-084` | Succeeded | ok | 40.6 | 0 |
| 85 | `fdycap-vhidn-085` | Succeeded | ok | 40.7 | 0 |
| 86 | `fdycap-vhidn-086` | Succeeded | ok | 40.5 | 0 |
| 87 | `fdycap-vhidn-087` | Succeeded | ok | 37.8 | 0 |
| 88 | `fdycap-vhidn-088` | Succeeded | ok | 38.5 | 0 |
| 89 | `fdycap-vhidn-089` | Succeeded | ok | 41.6 | 0 |
| 90 | `fdycap-vhidn-090` | Succeeded | ok | 37.9 | 0 |
| 91 | `fdycap-vhidn-091` | Succeeded | ok | 40.7 | 0 |
| 92 | `fdycap-vhidn-092` | Succeeded | ok | 41.8 | 0 |
| 93 | `fdycap-vhidn-093` | Succeeded | ok | 39.6 | 0 |
| 94 | `fdycap-vhidn-094` | Succeeded | ok | 39.7 | 0 |
| 95 | `fdycap-vhidn-095` | Succeeded | ok | 41.6 | 0 |
| 96 | `fdycap-vhidn-096` | Succeeded | ok | 38.7 | 0 |
| 97 | `fdycap-vhidn-097` | Succeeded | ok | 36.4 | 0 |
| 98 | `fdycap-vhidn-098` | Failed | model-quota | 21.7 | 0 |
| 99 | `fdycap-vhidn-099` | Error | account-cap | 2.7 | 0 |
| 100 | `fdycap-vhidn-100` | Error | account-cap | 3.7 | 0 |
| 101 | `fdycap-vhidn-101` | Error | account-cap | 4.2 | 0 |
| 102 | `fdycap-vhidn-102` | Error | account-cap | 4.4 | 0 |
