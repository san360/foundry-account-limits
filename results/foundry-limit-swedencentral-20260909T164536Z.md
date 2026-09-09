# Foundry account limit test - swedencentral

**Run (UTC):** 2026-09-09T16:44:33.545746+00:00 -> 2026-09-09T16:45:33.073135+00:00  
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
| Accounts created successfully | **2** |
| Total accounts now in region | **3** |
| Failures - account-count cap | 0 |
| Failures - model quota | 0 |
| Failures - capacity | 0 |
| Failures - transient | 0 |
| Failures - other | 0 |
| Model deployments created | 8 |
| Mean deployment duration (s) | 59.4 |
| Wall-clock duration (s) | 59.5 |
| Documented cap (Foundry resources/region/sub) | 100 |
| Cap reached in this run? | no |

## Verdict

**Cap not reached.** 2/2 attempts succeeded and 3 Foundry accounts now exist in `swedencentral`, below the documented cap of 100. Re-run with a higher `--target` to push further.

## Regional model quota at start of run

| Quota | Used | Limit | Headroom |
| --- | ---: | ---: | ---: |
| `OpenAI.GlobalStandard.gpt-5.4` | 0 | 1000 | 1000 |
| `OpenAI.GlobalStandard.gpt-5.4-mini` | 0 | 1000 | 1000 |
| `OpenAI.GlobalStandard.gpt-5.4-nano` | 0 | 5000 | 5000 |
| `OpenAI.GlobalStandard.gpt-5.4-pro` | 0 | 160 | 160 |
| `OpenAI.GlobalStandard.gpt-5.6-sol` | 0 | 1000 | 1000 |
| `OpenAI.GlobalStandard.text-embedding-3-large` | 0 | 1000 | 1000 |

## All attempts

| # | Account | Status | Class | Duration (s) | Models |
| ---: | --- | --- | --- | ---: | ---: |
| 1 | `fdysmk-qslox-001` | Succeeded | ok | 59.5 | 4 |
| 2 | `fdysmk-qslox-002` | Succeeded | ok | 59.2 | 4 |
