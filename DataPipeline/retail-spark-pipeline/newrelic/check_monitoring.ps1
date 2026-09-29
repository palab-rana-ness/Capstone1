param(
    [Parameter(Mandatory = $false)]
    [string]$AccountId = $env:NEW_RELIC_ACCOUNT_ID,

    [Parameter(Mandatory = $false)]
    [string]$UserApiKey = $env:NEW_RELIC_USER_API_KEY,

    [Parameter(Mandatory = $false)]
    [ValidateSet('us', 'eu')]
    [string]$Region = $(if ($env:NEW_RELIC_REGION) { $env:NEW_RELIC_REGION.ToLower() } else { 'us' }),

    [Parameter(Mandatory = $false)]
    [string]$ServiceName = $(if ($env:NEW_RELIC_SERVICE_NAME) { $env:NEW_RELIC_SERVICE_NAME } else { 'retail-spark-pipeline' }),

    [Parameter(Mandatory = $false)]
    [string]$PipelineId = $(if ($env:PIPELINE_ID) { $env:PIPELINE_ID } else { 'retail_data_pipeline' }),

    [Parameter(Mandatory = $false)]
    [string]$TenantId = 'tenant_001'
)

$ErrorActionPreference = 'Stop'

if ([string]::IsNullOrWhiteSpace($AccountId)) {
    throw 'Missing NEW_RELIC_ACCOUNT_ID (or pass -AccountId).'
}
if ([string]::IsNullOrWhiteSpace($UserApiKey)) {
    throw 'Missing NEW_RELIC_USER_API_KEY (or pass -UserApiKey).'
}

$endpoint = if ($Region -eq 'eu') { 'https://api.eu.newrelic.com/graphql' } else { 'https://api.newrelic.com/graphql' }

function Invoke-Nrql {
    param(
        [string]$Nrql
    )

        $query = @'
query($accountId: Int!, $nrql: Nrql!) {
    actor {
        account(id: $accountId) {
            nrql(query: $nrql) {
                results
            }
        }
    }
}
'@

        $payload = @{
                query = $query
                variables = @{
                        accountId = [int]$AccountId
                        nrql = ($Nrql.Replace("`r", ' ').Replace("`n", ' '))
                }
        } | ConvertTo-Json -Depth 10

    $headers = @{
        'Content-Type' = 'application/json'
        'API-Key' = $UserApiKey
    }

    $resp = Invoke-RestMethod -Method Post -Uri $endpoint -Headers $headers -Body $payload

    if ($resp.errors) {
        $err = ($resp.errors | ConvertTo-Json -Depth 5)
        throw "NerdGraph error: $err"
    }

    return $resp.data.actor.account.nrql.results
}

$checks = @(
    @{
        Name = 'Logs in last 30m'
        Query = "FROM Log SELECT count(*) AS value WHERE service_name = '$ServiceName' AND pipeline_id = '$PipelineId' SINCE 30 minutes ago"
        Key = 'value'
        WarnIfZero = $true
    },
    @{
        Name = 'Metrics in last 30m'
        Query = "FROM Metric SELECT count(*) AS value WHERE pipeline_id = '$PipelineId' SINCE 30 minutes ago"
        Key = 'value'
        WarnIfZero = $true
    },
    @{
        Name = 'Latest pipeline status'
        Query = "FROM Log SELECT latest(status) AS status WHERE event_type IN ('PIPELINE_END','PIPELINE_FAILURE') AND pipeline_id = '$PipelineId' FACET run_id, tenant_id SINCE 2 hours ago LIMIT 1"
        Key = 'status'
        WarnIfZero = $false
    },
    @{
        Name = 'Gold validation failures (60m)'
        Query = "FROM Metric SELECT sum(gold_validation_failures) AS value WHERE pipeline_id = '$PipelineId' SINCE 60 minutes ago"
        Key = 'value'
        WarnIfZero = $false
    },
    @{
        Name = 'API errors (60m)'
        Query = "FROM Metric SELECT sum(api_error_count) AS value WHERE pipeline_id = '$PipelineId' SINCE 60 minutes ago"
        Key = 'value'
        WarnIfZero = $false
    },
    @{
        Name = 'Silver invalid records (60m)'
        Query = "FROM Metric SELECT sum(silver_invalid_records) AS value WHERE pipeline_id = '$PipelineId' AND tenant_id = '$TenantId' SINCE 60 minutes ago"
        Key = 'value'
        WarnIfZero = $false
    }
)

$results = @()
$hasWarning = $false

foreach ($check in $checks) {
    $nrqlResults = Invoke-Nrql -Nrql $check.Query
    if (-not $nrqlResults -or $nrqlResults.Count -eq 0) {
        $results += [pscustomobject]@{
            Check = $check.Name
            Value = '<no rows>'
            State = 'WARN'
        }
        $hasWarning = $true
        continue
    }

    $row = $nrqlResults[0]
    $value = $row.($check.Key)

    $state = 'OK'
    if ($check.WarnIfZero -and ([double]($value | ForEach-Object { $_ }) -eq 0)) {
        $state = 'WARN'
        $hasWarning = $true
    }

    if ($check.Name -eq 'Latest pipeline status' -and $value -eq 'FAILED') {
        $state = 'FAIL'
        $hasWarning = $true
    }

    $results += [pscustomobject]@{
        Check = $check.Name
        Value = $value
        State = $state
    }
}

Write-Host ''
Write-Host 'New Relic Monitoring Check' -ForegroundColor Cyan
Write-Host "Region: $Region | AccountId: $AccountId | PipelineId: $PipelineId"
$results | Format-Table -AutoSize
Write-Host ''
Write-Host 'Tip: use newrelic/NRQL_QUERIES.md for deeper drill-down queries.'

if ($hasWarning) {
    exit 2
}

exit 0
