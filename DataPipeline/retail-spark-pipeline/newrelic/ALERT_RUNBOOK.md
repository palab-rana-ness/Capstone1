# New Relic Alert Runbook (No Dashboard)

This runbook creates monitoring outcomes without a dashboard UI.

## Prerequisites

- Pipeline emits telemetry (NEW_RELIC_LICENSE_KEY and NEW_RELIC_REGION already set).
- You can run NRQL in New Relic.

## Alert Policy (recommended)

Create one policy: Retail Data Pipeline Alerts

### Condition 1: Pipeline failure event

- Query:

```sql
FROM Log SELECT count(*)
WHERE event_type = 'PIPELINE_FAILURE'
AND pipeline_id = 'retail_data_pipeline'
```

- Critical threshold: above 0 for at least 5 minutes.

### Condition 2: Gold validation failures

- Query:

```sql
FROM Metric SELECT sum(gold_validation_failures)
WHERE pipeline_id = 'retail_data_pipeline'
```

- Critical threshold: above 0 for at least 5 minutes.

### Condition 3: API errors during ingestion

- Query:

```sql
FROM Metric SELECT sum(api_error_count)
WHERE pipeline_id = 'retail_data_pipeline'
```

- Warning threshold: above 0 for at least 10 minutes.

### Condition 4: High silver invalid ratio

If your account supports arithmetic in NRQL alerts, use:

```sql
FROM Metric SELECT (sum(silver_invalid_records) / max(sum(silver_input_records), 1))
WHERE pipeline_id = 'retail_data_pipeline'
```

- Critical threshold: above 0.10 for at least 10 minutes.

If arithmetic is restricted in your account, use a fallback absolute condition:

```sql
FROM Metric SELECT sum(silver_invalid_records)
WHERE pipeline_id = 'retail_data_pipeline'
```

- Warning threshold: above 10 for at least 10 minutes.

### Condition 5: Missing successful completion

- Query:

```sql
FROM Log SELECT count(*)
WHERE event_type = 'PIPELINE_END'
AND status = 'SUCCESS'
AND pipeline_id = 'retail_data_pipeline'
```

- Loss of signal / no data behavior: alert if value stays below 1 over your expected run interval.
- Example: if pipeline runs hourly, evaluate over 2 hours.

## Incident triage flow

1. Find failing run:

```sql
FROM Log SELECT latest(run_id)
WHERE event_type IN ('PIPELINE_FAILURE', 'GOLD_FAILURE', 'SILVER_FAILURE', 'BRONZE_FAILURE')
AND pipeline_id = 'retail_data_pipeline'
SINCE 6 hours ago
```

2. Pull run timeline:

```sql
FROM Log SELECT timestamp, event_type, level, stage, dataset, status, message
WHERE run_id = '<RUN_ID>'
AND pipeline_id = 'retail_data_pipeline'
SINCE 24 hours ago
LIMIT 500
```

3. Quantify impact:

```sql
FROM Metric SELECT sum(silver_invalid_records), sum(silver_quarantine_records), sum(gold_validation_failures)
WHERE run_id = '<RUN_ID>'
AND pipeline_id = 'retail_data_pipeline'
FACET tenant_id, dataset
SINCE 24 hours ago
```

4. Re-run pipeline for affected tenant and verify recovery using the same queries.
