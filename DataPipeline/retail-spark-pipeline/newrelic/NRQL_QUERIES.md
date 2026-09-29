# New Relic NRQL Query Pack (No Dashboard Required)

Use these queries in New Relic Query Builder to monitor the pipeline directly.

## 1) Is telemetry arriving?

```sql
FROM Log SELECT count(*)
WHERE service_name = 'retail-spark-pipeline'
SINCE 30 minutes ago
```

```sql
FROM Metric SELECT count(*)
WHERE pipeline_id = 'retail_data_pipeline'
SINCE 30 minutes ago
```

## 2) Latest run status

```sql
FROM Log SELECT latest(status)
WHERE event_type IN ('PIPELINE_END', 'PIPELINE_FAILURE')
AND pipeline_id = 'retail_data_pipeline'
FACET run_id, tenant_id
SINCE 2 hours ago
```

## 3) Stage event visibility

```sql
FROM Log SELECT count(*)
WHERE pipeline_id = 'retail_data_pipeline'
FACET event_type
SINCE 60 minutes ago
```

## 4) Bronze throughput

```sql
FROM Metric SELECT sum(bronze_records_written)
WHERE pipeline_id = 'retail_data_pipeline'
FACET dataset, tenant_id
TIMESERIES 5 minutes
SINCE 60 minutes ago
```

## 5) Silver quality

```sql
FROM Metric SELECT sum(silver_input_records), sum(silver_invalid_records), sum(silver_quarantine_records)
WHERE pipeline_id = 'retail_data_pipeline'
FACET dataset, tenant_id
SINCE 60 minutes ago
```

## 6) Gold health

```sql
FROM Metric SELECT sum(gold_output_records), sum(gold_validation_failures)
WHERE pipeline_id = 'retail_data_pipeline'
FACET tenant_id
SINCE 60 minutes ago
```

## 7) Pipeline latency

```sql
FROM Metric SELECT average(pipeline_duration_seconds)
WHERE pipeline_id = 'retail_data_pipeline'
FACET tenant_id
TIMESERIES 5 minutes
SINCE 60 minutes ago
```

## 8) API error visibility

```sql
FROM Metric SELECT sum(api_error_count)
WHERE pipeline_id = 'retail_data_pipeline'
FACET dataset, tenant_id
SINCE 60 minutes ago
```

## 9) Focus a single run

Replace <RUN_ID> with a run id from pipeline output.

```sql
FROM Log SELECT *
WHERE run_id = '<RUN_ID>'
AND pipeline_id = 'retail_data_pipeline'
SINCE 24 hours ago
LIMIT 200
```

## 10) Focus one tenant

```sql
FROM Log SELECT count(*)
WHERE tenant_id = 'tenant_001'
AND pipeline_id = 'retail_data_pipeline'
FACET event_type
SINCE 6 hours ago
```
