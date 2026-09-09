/*
  Microsoft Foundry account - "basic mode" (basic agent setup) deployment unit.

  Deploys ONE Foundry account (Microsoft.CognitiveServices/accounts, kind=AIServices)
  with project management enabled, one Foundry project, and a set of Global Standard
  model deployments.

  "Basic mode" == basic agent setup: agent threads/files/vector stores live in
  Microsoft-managed, logically-isolated storage. No BYO Cosmos DB / AI Search /
  Storage account and no capability host is created. This is the default when no
  customer-owned resources are configured.

  This template is the *unit of scale* used by scripts/foundry_limit_test.py, which
  deploys it N times to empirically find the per-region account cap.
*/

targetScope = 'resourceGroup'

@description('Name of the Foundry account. Must be globally unique (used as the custom subdomain).')
@minLength(3)
@maxLength(60)
param accountName string

@description('Azure region for the Foundry account. Must support Foundry + the requested models.')
param location string = resourceGroup().location

@description('Name of the Foundry project created inside the account.')
param projectName string = 'proj-default'

@description('Friendly display name for the Foundry project.')
param projectDisplayName string = projectName

@description('SKU for the Foundry account. S0 is the only standard (non-free) tier; only one F0 account per type per subscription is allowed.')
@allowed([
  'S0'
  'F0'
])
param skuName string = 'S0'

@description('Model deployments to create on the account. All use the Global Standard deployment type.')
param modelDeployments array = [
  {
    name: 'gpt-5.6-sol'
    model: 'gpt-5.6-sol'
    version: '2026-07-09'
    capacity: 1
  }
  {
    name: 'gpt-5.4'
    model: 'gpt-5.4'
    version: '2026-03-05'
    capacity: 1
  }
  {
    name: 'gpt-5.4-nano'
    model: 'gpt-5.4-nano'
    version: '2026-03-17'
    capacity: 1
  }
  {
    name: 'text-embedding-3-large'
    model: 'text-embedding-3-large'
    version: '1'
    capacity: 1
  }
]

@description('Deployment SKU applied to every model deployment.')
@allowed([
  'GlobalStandard'
  'DataZoneStandard'
  'Standard'
])
param deploymentSku string = 'GlobalStandard'

@description('Set false to skip model deployments and provision the account/project only (fast account-cap probing).')
param deployModels bool = true

@description('Set false to skip the Foundry project (account-only probing).')
param deployProject bool = true

@description('Tags applied to the account.')
param tags object = {}

// ---------------------------------------------------------------------------
// Foundry account (kind = AIServices, project management enabled)
// ---------------------------------------------------------------------------
resource account 'Microsoft.CognitiveServices/accounts@2026-07-01' = {
  name: accountName
  location: location
  kind: 'AIServices'
  sku: {
    name: skuName
  }
  identity: {
    type: 'SystemAssigned'
  }
  tags: tags
  properties: {
    // Required for the account to host Foundry projects / agents.
    allowProjectManagement: true
    // Required for token-based (Entra) data-plane access and for the
    // https://<name>.services.ai.azure.com endpoint.
    customSubDomainName: accountName
    publicNetworkAccess: 'Enabled'
    disableLocalAuth: false
    networkAcls: {
      defaultAction: 'Allow'
    }
  }
}

// ---------------------------------------------------------------------------
// Foundry project - basic agent setup (no capability host, no BYO resources)
// ---------------------------------------------------------------------------
resource project 'Microsoft.CognitiveServices/accounts/projects@2026-07-01' = if (deployProject) {
  parent: account
  name: projectName
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    displayName: projectDisplayName
    description: 'Basic-mode Foundry project (Microsoft-managed agent storage).'
  }
}

// ---------------------------------------------------------------------------
// Model deployments - Global Standard.
// batchSize(1) serializes them: concurrent write operations against the same
// Cognitive Services account return 409 Conflict.
// ---------------------------------------------------------------------------
@batchSize(1)
resource deployments 'Microsoft.CognitiveServices/accounts/deployments@2026-07-01' = [
  for m in (deployModels ? modelDeployments : []): {
    parent: account
    name: m.name
    sku: {
      name: deploymentSku
      capacity: m.capacity
    }
    properties: {
      model: {
        format: 'OpenAI'
        name: m.model
        version: string(m.version)
      }
      versionUpgradeOption: 'OnceNewDefaultVersionAvailable'
      raiPolicyName: 'Microsoft.DefaultV2'
    }
  }
]

// ---------------------------------------------------------------------------
// Outputs
// ---------------------------------------------------------------------------
output accountId string = account.id
output accountName string = account.name
output location string = account.location
output endpoint string = 'https://${accountName}.services.ai.azure.com'
output endpoints object = account.properties.?endpoints ?? {}
output projectEndpoint string = deployProject ? 'https://${accountName}.services.ai.azure.com/api/projects/${projectName}' : ''
output principalId string = account.identity.principalId
output deployedModels array = deployModels ? map(modelDeployments, m => m.name) : []
