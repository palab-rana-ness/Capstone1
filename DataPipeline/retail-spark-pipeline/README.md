# Retail AWS Data Pipeline (FastAPI -> PySpark -> S3 Bronze/Silver/Gold)

An end-to-end, production-style MVP data pipeline that ingests data from the
existing retail FastAPI mock server, processes it with PySpark, and stores
Bronze / Silver / Gold layers in Amazon S3 as Parquet.

```
                    ┌─────────────────────────┐
                    │   Retail FastAPI APIs   │
                    │  Products / Sales /      │
                    │  Inventory / Promotions / │
                    │  Suppliers               │
                    └────────────┬────────────┘
                                 │ HTTP / JSON
                                 ▼
                    ┌─────────────────────────┐
                    │   PySpark Ingestion     │
                    └────────────┬────────────┘
                                 ▼
             ┌────────────────────────────────────┐
             │              AWS S3               │
             │  bronze/  silver/  gold/           │
             │  quarantine/  logs/                │
             └────────────────────────────────────┘
                                 ▼
                       Pricing / Analytics
```

## 1. Architecture

Three S3-backed layers, each with a strictly separated responsibility
(section 53 of the spec):

| Layer | Responsibility | NOT allowed |
|---|---|---|
| **Bronze** | Ingest FastAPI JSON as-is + traceability metadata | business calculations, pricing, aggregation |
| **Silver** | Schema-on-write, validation, cleansing, dedup, quarantine | business/pricing calculations |
| **Gold** | Joins, aggregation, pricing, promotion/inventory enrichment | — |

Data flow: `FastAPI -> PySpark ingestion -> S3 Bronze -> PySpark validation/cleansing -> S3 Silver -> PySpark transformation/enrichment -> S3 Gold -> Pricing/Analytics`.

This pipeline is a **separate project** from the existing FastAPI mock server
(`../app`) -- it only consumes that server's HTTP API and never modifies it.

## 2. AWS S3 structure

```
s3://<bucket>/
    bronze/{products,sales,inventory,promotions,suppliers,promotion_products,customers,stores,categories}/
        tenant_id=<tenant>/ingestion_date=<yyyy-mm-dd>/*.parquet

    silver/{...same datasets, plus sales_items...}/
        tenant_id=<tenant>/processing_date=<yyyy-mm-dd>/*.parquet

    gold/pricing/            tenant_id=<tenant>/business_date=<yyyy-mm-dd>/*.parquet
    gold/product_sales/      tenant_id=<tenant>/business_date=<yyyy-mm-dd>/*.parquet

    quarantine/{products,sales,sales_items,inventory,promotions,suppliers,...}/
        tenant_id=<tenant>/processing_date=<yyyy-mm-dd>/*.parquet

    logs/ingestion/tenant_id=<tenant>/run_id=<run_id>/*.json
    logs/quality/tenant_id=<tenant>/run_id=<run_id>/*.json
    logs/pipeline/tenant_id=<tenant>/run_id=<run_id>/*.json
```

All datasets are Parquet. Writes use `partitionOverwriteMode=dynamic`, so a
rerun only replaces the specific `tenant_id`/`*_date` partitions it produces
-- never the whole dataset (section 42).

## 3. Source APIs (existing FastAPI server, unmodified)

| Dataset | Endpoint | source_system |
|---|---|---|
| products | `GET /api/v1/products` | product_api |
| sales | `GET /api/v1/sales/transactions` (order + nested items in one paginated call) | sales_database |
| inventory | `GET /api/v1/inventory` | inventory_api |
| promotions | `GET /api/v1/promotions` | promotion_api |
| suppliers | `GET /api/v1/suppliers` | supplier_api |
| customers | `GET /api/v1/customers` | sales_database |
| stores | `GET /api/v1/stores` | sales_database |
| categories | `GET /api/v1/categories` | product_database |
| promotion_products (derived) | `GET /api/v1/products/{product_id}/promotions`, called once per ingested product | promotion_api |

**Why `/sales/transactions` instead of `/sales/orders` + per-order `/items`:**
it returns each order with its nested items in one paginated response, so
Bronze stays a single efficient bulk call instead of N+1 requests. Silver
then explodes the nested `items` array into a separate trusted `sales_items`
table (see `src/silver/silver_transform.py::transform_sales`).

**Why per-product `/promotions` for `promotion_products`:** the FastAPI
source has no bulk endpoint for the promotion<->product relationship, only
this per-product one. Bronze ingestion calls it once per already-ingested
product to derive the relationship table needed for Gold promotion
enrichment (section 35).

Every call sends `X-Tenant-ID` and paginates with `limit`/`offset` until
`pagination.has_more` is `false` (`src/ingestion/paginator.py`) -- never
assumes a single response contains the full dataset.

## 4. Bronze layer

Bronze stays close to the source. The only transformations applied
(`src/ingestion/bronze_ingestion.py`) are:

- attaching `tenant_id` (always the X-Tenant-ID-validated value, never
  trusted from the response body), `pipeline_id`, `run_id`, `source_system`,
  `ingestion_timestamp`, `ingestion_date`
- `spark.createDataFrame(records)` for basic schema compatibility

No pricing, margin, revenue or aggregation logic ever runs in Bronze.

## 5. Silver layer

`src/silver/silver_transform.py` reads Bronze, then applies (per dataset):

1. explicit schema cast (`src/silver/schema.py` -- `product_id: StringType`,
   `unit_price: DecimalType(18,4)`, `created_at: TimestampType`, etc. --
   never relies on inferred schema)
2. timestamp normalization (`to_timestamp`) and categorical normalization
   (trim + uppercase status/type fields) -- `src/silver/cleansing.py`
3. duplicate handling: keep the latest record per business key, ordered by
   `updated_at` (section 29)
4. required-field + business-rule validation, producing a
   `validation_errors` array column (`src/silver/validation.py`, sections
   26/28)
5. split into trusted Silver (valid) vs. Quarantine (invalid, with
   `validation_error` + `validation_timestamp`)
6. quality metrics written to `logs/quality/` (section 30)

### Business keys used for deduplication (section 29)

| Dataset | Key |
|---|---|
| products | tenant_id + product_id |
| suppliers | tenant_id + supplier_id |
| inventory | tenant_id + inventory_id |
| promotions | tenant_id + promotion_id |
| sales (orders) | tenant_id + order_id |
| sales_items | tenant_id + order_item_id |

## 6. Gold layer

`src/gold/gold_transform.py` reads only trusted Silver and builds two
datasets:

### gold_pricing

Formulas (also documented as comments in `src/gold/pricing.py`):

```
unit_discount =
    0                                                            if no active promotion
    MIN(base_price * discount_value / 100, maximum_discount, base_price)   if PERCENTAGE
    MIN(discount_value, maximum_discount, base_price)                      if FIXED_AMOUNT

final_price = base_price - unit_discount            # per unit, always >= 0
net_price   = final_price * (1 + tax_rate / 100)    # per unit, tax-inclusive

gross_amount    = quantity_sold * base_price        # aggregate, at catalog price
discount_amount = quantity_sold * unit_discount      # aggregate, always <= gross_amount
```

A promotion is only "applicable" if `status == ACTIVE` and
`start_date <= business_date <= end_date` (section 35). If a product matches
several active promotions, the one with the highest `discount_value` wins
(deterministic tie-break by `promotion_id`).

### gold_product_sales

Historical sales performance per product: `total_quantity_sold`,
`gross_revenue`, `discount_amount` (actual, from recorded sales, not the
catalog promotion), `net_revenue`, `average_selling_price =
net_revenue / total_quantity_sold` (0 when no sales), `inventory_available`.

### Gold validation (section 40)

Before Gold is marked `SUCCESS`, `src/quality/quality_checks.py` checks:
`tenant_id`/`product_id` not null, no duplicate `(tenant_id, product_id)`
keys, `final_price >= 0`, `discount_amount <= gross_amount`. Any failure sets
`gold_status = FAILED` and **the Gold dataset is not written** -- an invalid
Gold dataset is never published as successful.

## 7. Multi-tenancy & traceability

Every Bronze/Silver/Gold record retains `tenant_id`. All cross-dataset joins
are keyed on `(tenant_id, <business_key>)`, never the business key alone
(section 9) -- see `src/gold/enrichment.py`. `tenant_id`, `pipeline_id`,
`run_id`, `source_system`, `ingestion_timestamp` survive Bronze -> Silver ->
Gold so any Gold record can be traced back to the exact pipeline execution
that produced it (`src/utils/run_id.py` generates one `run_id` per run,
threaded through every stage).

## 8. Data quality & quarantine

Invalid Silver records (missing required fields or failing business rules,
sections 26/28) are written to `quarantine/<dataset>/` with the original
fields plus `validation_error` and `validation_timestamp`. Quality metrics
(input/valid/invalid/duplicate/output counts, section 30) are written as JSON
to `logs/quality/`.

## 9. S3 partitioning

- Bronze: `tenant_id=<tenant>/ingestion_date=<yyyy-mm-dd>/`
- Silver / Quarantine: `tenant_id=<tenant>/processing_date=<yyyy-mm-dd>/`
- Gold: `tenant_id=<tenant>/business_date=<yyyy-mm-dd>/`

## 10. AWS authentication & IAM permissions

AWS credentials are **never** hardcoded anywhere in this project. Spark/boto3
resolve them through the standard credential provider chain: environment
variables -> `AWS_PROFILE` / `~/.aws/credentials` -> EC2/ECS/EKS instance
role. `.env` only holds non-secret configuration (region, bucket name,
pipeline id) and is git-ignored; `.env.example` is committed instead.

Minimum IAM policy for the Spark execution identity:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:ListBucket"],
      "Resource": "arn:aws:s3:::<bucket>"
    },
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"],
      "Resource": "arn:aws:s3:::<bucket>/*"
    }
  ]
}
```

`s3:DeleteObject` is only required because Silver/Gold/Bronze writes use
`mode("overwrite")` on individual partitions (Spark deletes the old
partition's files before writing new ones).

## 11. Spark S3A configuration

`src/utils/spark_session.py` builds a SparkSession with:

- `spark.hadoop.fs.s3a.impl = org.apache.hadoop.fs.s3a.S3AFileSystem`
- `spark.jars.packages = org.apache.hadoop:hadoop-aws:<version>,<aws-sdk-group>:<artifact>:<version>`
- `spark.sql.session.timeZone = UTC`
- `spark.sql.sources.partitionOverwriteMode = dynamic` (safe reruns)

**Version pinning matters.** This project's `requirements.txt` pins
`pyspark>=4.0.0`. PySpark 4.x bundles **Hadoop client 3.5.0** (no
`hadoop-aws` jar included by default), so the default config uses:

- `org.apache.hadoop:hadoop-aws:3.5.0`
- `software.amazon.awssdk:bundle:2.29.52` (Hadoop 3.4+ moved from the AWS SDK
  v1 `com.amazonaws:aws-java-sdk-bundle` to the AWS SDK v2 `bundle` artifact)

If your environment uses an older Spark 3.x build (Hadoop 3.3.x client),
override via environment variables:

```
HADOOP_AWS_VERSION=3.3.4
AWS_JAVA_SDK_GROUP=com.amazonaws
AWS_JAVA_SDK_ARTIFACT=aws-java-sdk-bundle
AWS_JAVA_SDK_VERSION=1.12.262
```

Always verify the exact Hadoop client version bundled with your installed
PySpark (`pyspark/jars/hadoop-client-*.jar`) and pick a matching
`hadoop-aws` release from Maven Central -- mismatched versions are the most
common cause of `NoSuchMethodError`/`ClassNotFoundException` with S3A.

No credentials-provider classname is hardcoded; Hadoop S3A's built-in default
chain resolves credentials automatically, which works across both AWS SDK
v1- and v2-based `hadoop-aws` releases.

## 12. Installation

```powershell
cd retail-spark-pipeline
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
# edit .env: set S3_BUCKET to a bucket you own (bucket names are globally
# unique across ALL of AWS -- generic names like "retail-data-lake-dev" are
# almost always already taken by someone else)
```

### Java requirement

PySpark requires a JVM. **This environment does not have Java installed**,
so the pipeline's Spark stages (Bronze write / Silver / Gold) cannot be
executed here -- only the non-Spark parts (FastAPI ingestion client,
pagination, config, S3 connectivity via boto3) have been verified. To
actually run the pipeline:

1. Install a JDK (Java 17 recommended): `winget install EclipseAdoptium.Temurin.17.JDK`
2. Ensure `JAVA_HOME` is set and `java` is on `PATH`
3. Re-run `pytest tests/` -- the Spark-gated tests will stop skipping automatically

## 13. Running the existing FastAPI source server

This pipeline does not modify or ship the FastAPI server. Start it from the
sibling project (`../app`):

```powershell
cd ..
uvicorn app.main:app --reload
```

It listens on `http://127.0.0.1:8000` by default -- matching `FASTAPI_BASE_URL`
in `.env.example`. (Note: on this machine, `http://localhost:8000` can
resolve to a different, unrelated listener that returns a generic 404 for
every path -- always use `127.0.0.1` explicitly if you see unexpected 404s.)

## 14. Running the pipeline

```powershell
# Full load for one tenant
python run_pipeline.py --tenant-id tenant_001 --mode full

# Full load for all tenants
python run_pipeline.py --tenant-id all --mode full

# Incremental load (uses the FastAPI updated_since parameter)
python run_pipeline.py --tenant-id tenant_001 --mode incremental --updated-since 2026-09-24T00:00:00Z
```

Example console output:

```
=========================================
RETAIL AWS DATA PIPELINE
=========================================

Pipeline ID:
retail_data_pipeline

Run ID:
20260925_143015_a83f21

Tenant:
tenant_001

Mode:
FULL

S3 Bucket:
retail-data-lake-dev-590183679875

[1/3] FASTAPI -> S3 BRONZE

Products:      50
Sales:         1000
Inventory:     550
Promotions:    50
Suppliers:     10
Customers:     100
Stores:        10
Categories:    10
Promotion Links: 187

Status: SUCCESS

[2/3] S3 BRONZE -> S3 SILVER

Products:
Input: 50
Valid: 47
Invalid: 3
...

Status: SUCCESS

[3/3] S3 SILVER -> S3 GOLD

Pricing records: 47
Product sales records: 47

Status: SUCCESS

=========================================
PIPELINE COMPLETED
=========================================

Overall Status: SUCCESS
```

Every run also writes JSON logs to S3 under `logs/ingestion/`,
`logs/quality/`, and `logs/pipeline/` for the given `tenant_id`/`run_id`.

## 15. Testing

```powershell
pytest tests/ -v
```

Tests are split into two groups:

- **Always runnable** (no Java required): `test_config.py`, `test_run_id.py`,
  `test_api_client.py`, `test_paginator.py`,
  `test_s3_connectivity.py::test_s3_bucket_is_reachable` /
  `test_boto3_can_write_and_read_test_prefix` (real boto3 S3 round-trip
  against a `test/` prefix -- never touches bronze/silver/gold/quarantine)
- **Spark-gated** (auto-skip without Java, via the `spark` fixture in
  `tests/conftest.py`): schema validation, business-rule validation
  (price/quantity/discount), duplicate handling, Gold pricing calculations,
  Gold validation failures, tenant-isolation (a tenant_001 product must never
  join tenant_002 inventory), and the full S3A Spark read/write round-trip

## 16. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `NoSuchMethodError` / `ClassNotFoundException` on Spark startup | `hadoop-aws` version doesn't match the Hadoop client bundled with your PySpark | Check `pyspark/jars/hadoop-client-*.jar` version and set matching `HADOOP_AWS_VERSION` |
| `java.lang.UnsupportedClassVersionError` | JDK too old/new for this Spark build | Use JDK 17 (or the version documented for your Spark release) |
| Connection refused to FastAPI | Source server not running | `cd ../ && uvicorn app.main:app --reload` |
| 404 from FastAPI via `localhost` but 200 via `127.0.0.1` | `localhost` resolves to an unrelated listener on this machine | Always use `127.0.0.1` in `FASTAPI_BASE_URL` |
| `403 Forbidden` on `head_bucket` | Bucket name already taken by another AWS account (S3 names are globally unique) | Pick a more unique bucket name, e.g. suffix with your account ID |
| `pyspark` import works but `SparkSession.builder.getOrCreate()` fails | No JVM/Java installed | Install a JDK (see section 12) |
| Gold status is `FAILED` | A `validate_gold_pricing` check failed (see section 6) | Inspect `logs/pipeline/` for `validation_failures`; Gold is intentionally not published |

## 17. New Relic Observability Architecture

The existing FastAPI -> Bronze -> Silver -> Gold flow is unchanged. Observability is layered on top via OpenTelemetry OTLP.

```
              FASTAPI SOURCES
                  |
                  v
              PYSPARK PIPELINE
                  |
       +---------------+----------------+
       |               |                |
       v               v                v
     BRONZE           SILVER            GOLD
       |               |                |
       +---------------+----------------+
                  |
                  v
              S3 DATA LAKE

              PYSPARK
                |
         +----------+----------+
         |                     |
         v                     v
       LOGGING               METRICS
         |                     |
         +----------+----------+
                v
            OPENTELEMETRY
                |
                OTLP
                |
                v
            NEW RELIC CLOUD
                |
        +-----------+-----------+
        v           v           v
       Logs       Metrics    Dashboard
                |
               Alerts
```

Implementation modules:

- `observability/logging_config.py`: structured JSON event logging
- `observability/metrics.py`: custom metric instruments
- `observability/newrelic_exporter.py`: region-aware OTLP providers
- `observability/telemetry.py`: non-blocking telemetry facade

## 18. New Relic Account Setup (Manual)

Account creation is intentionally manual (no credentials in code):

1. Sign up or log in at New Relic.
2. Select your region (`US` or `EU`) in New Relic.
3. Open your target account/workspace.
4. Generate/copy a License key for OTLP ingest.
5. Set local environment values in `.env` (never commit):
  - `NEW_RELIC_LICENSE_KEY=<your_key>`
  - `NEW_RELIC_REGION=us` or `NEW_RELIC_REGION=eu`
  - `NEW_RELIC_SERVICE_NAME=retail-spark-pipeline`

OTLP endpoints selected automatically by region:

- `us` -> `https://otlp.nr-data.net:4318`
- `eu` -> `https://otlp.eu01.nr-data.net:4318`

## 19. Environment Configuration

Use `.env.example` as template. Required keys for observability:

- `PIPELINE_ID=retail_data_pipeline`
- `ENVIRONMENT=dev`
- `NEW_RELIC_LICENSE_KEY=`
- `NEW_RELIC_REGION=us`
- `NEW_RELIC_SERVICE_NAME=retail-spark-pipeline`
- `SILVER_INVALID_RATE_THRESHOLD=0.10`

Security controls:

- `.env` is git-ignored.
- License key is never hardcoded in source.
- Telemetry payloads are sanitized to drop secret-like attributes.

## 20. Structured Events and Metrics

### Structured event schema

Each major event includes at least:

- `timestamp`
- `level`
- `message`
- `pipeline_id`
- `run_id`
- `tenant_id`
- `stage`
- `dataset`
- `status`

Required event types emitted:

- `PIPELINE_START`, `PIPELINE_END`, `PIPELINE_FAILURE`
- `BRONZE_START`, `BRONZE_END`, `BRONZE_FAILURE`
- `SILVER_START`, `SILVER_END`, `SILVER_FAILURE`
- `GOLD_START`, `GOLD_END`, `GOLD_FAILURE`
- `DATA_QUALITY_FAILURE`, `S3_READ_FAILURE`, `S3_WRITE_FAILURE`, `API_FAILURE`, `QUARANTINE_RECORDS`

### Custom metrics emitted

- `pipeline_run_count`, `pipeline_success_count`, `pipeline_failure_count`, `pipeline_duration_seconds`
- `bronze_records_ingested`, `bronze_records_written`, `bronze_duration_seconds`
- `silver_input_records`, `silver_valid_records`, `silver_invalid_records`, `silver_duplicate_records`, `silver_quarantine_records`, `silver_duration_seconds`
- `gold_input_records`, `gold_output_records`, `gold_validation_failures`, `gold_duration_seconds`
- `s3_read_duration_seconds`, `s3_write_duration_seconds`
- `api_request_count`, `api_error_count`, `api_request_duration_seconds`
- data-quality counters: `input_record_count`, `valid_record_count`, `invalid_record_count`, `duplicate_record_count`, `null_violation_count`, `business_rule_violation_count`, `referential_integrity_failure_count`, `quarantine_record_count`

Common attributes:

- `pipeline_id`
- `run_id`
- `tenant_id`
- `stage`
- `dataset`
- `environment`

## 21. Dashboard Setup (Retail Data Pipeline Monitoring)

In New Relic Dashboards, create one dashboard named `Retail Data Pipeline Monitoring` with widgets for:

1. Pipeline overview: total runs, success runs, failed runs, avg duration, latest status.
2. Bronze: ingested/written records, ingestion duration, API errors.
3. Silver: processed/valid/invalid/duplicate/quarantine counts.
4. Gold: input/output counts, validation failures, pricing/product-sales output trends.
5. Tenant monitoring: grouped by `tenant_id`.
6. Pipeline health: SUCCESS/FAILED/RUNNING status and duration.

## 22. Monitoring Without Dashboard UI

If you do not want to create a dashboard, use the non-UI monitoring pack in:

- `newrelic/NRQL_QUERIES.md`: copy/paste NRQL queries for run status, stage visibility, throughput, quality, and latency.
- `newrelic/ALERT_RUNBOOK.md`: alert conditions and incident triage flow.
- `newrelic/check_monitoring.ps1`: command-line health check against NerdGraph API.

Run the checker:

```powershell
cd retail-spark-pipeline
$env:NEW_RELIC_ACCOUNT_ID = "<your_account_id>"
$env:NEW_RELIC_USER_API_KEY = "<your_user_api_key>"
./newrelic/check_monitoring.ps1
```

Notes:

- `NEW_RELIC_USER_API_KEY` is different from `NEW_RELIC_LICENSE_KEY`.
- Exit code is `0` for OK, `2` if warnings/failures are detected.
- If your network blocks `otlp.nr-data.net:4318`/`otlp.eu01.nr-data.net:4318`, set
  `NEW_RELIC_OTLP_ENDPOINT` to a reachable internal OTLP gateway URL.

## 22. Example NRQL Queries

Use the following patterns (adjust account and time windows as needed):

1. Recent pipeline runs
  - `SELECT count(*) FROM Log WHERE event_type = 'PIPELINE_START' FACET pipeline_id SINCE 24 hours ago`
2. Pipeline failures
  - `SELECT count(*) FROM Log WHERE event_type = 'PIPELINE_FAILURE' FACET tenant_id SINCE 24 hours ago`
3. Silver invalid records
  - `SELECT sum(silver_invalid_records) FROM Metric WHERE pipeline_id = 'retail_data_pipeline' FACET tenant_id, dataset SINCE 24 hours ago`
4. Gold validation failures
  - `SELECT sum(gold_validation_failures) FROM Metric WHERE pipeline_id = 'retail_data_pipeline' FACET tenant_id SINCE 24 hours ago`
5. Pipeline duration
  - `SELECT average(pipeline_duration_seconds) FROM Metric WHERE pipeline_id = 'retail_data_pipeline' TIMESERIES`
6. Records processed
  - `SELECT sum(bronze_records_written), sum(silver_valid_records), sum(gold_output_records) FROM Metric WHERE pipeline_id = 'retail_data_pipeline' SINCE 24 hours ago`
7. Tenant-level throughput
  - `SELECT sum(gold_output_records) FROM Metric WHERE pipeline_id = 'retail_data_pipeline' FACET tenant_id SINCE 24 hours ago`
8. Bronze ingestion failures
  - `SELECT count(*) FROM Log WHERE event_type = 'BRONZE_FAILURE' FACET dataset, tenant_id SINCE 24 hours ago`
9. API failures
  - `SELECT count(*) FROM Log WHERE event_type = 'API_FAILURE' FACET dataset, tenant_id SINCE 24 hours ago`
10. S3 failures
  - `SELECT count(*) FROM Log WHERE event_type IN ('S3_READ_FAILURE', 'S3_WRITE_FAILURE') FACET stage, dataset SINCE 24 hours ago`

## 23. Alert Conditions (Recommended)

Configure alerts in the New Relic UI:

1. Pipeline failure: trigger when `PIPELINE_FAILURE` count > 0 over 5 minutes.
2. Silver invalid rate high: `sum(silver_invalid_records) / max(sum(silver_input_records),1)` > `SILVER_INVALID_RATE_THRESHOLD`.
3. Duplicate rate high: `sum(silver_duplicate_records) / max(sum(silver_input_records),1)` above threshold.
4. Gold validation failure: `sum(gold_validation_failures)` > 0 over 5-10 minutes.
5. Pipeline duration anomaly: `average(pipeline_duration_seconds)` outside expected baseline.
6. S3 write failure: `S3_WRITE_FAILURE` log count > 0 over 5 minutes.
7. API failure rate: `sum(api_error_count) / max(sum(api_request_count),1)` above threshold.

Notification channels are intentionally not hardcoded. Configure destinations in your account.

## 24. Verification and Test Procedure

### Standard run verification

1. Start FastAPI source server.
2. Run pipeline:
  - `python run_pipeline.py --tenant-id tenant_001 --mode full`
3. Confirm Bronze/Silver/Gold still succeed exactly as before.
4. In New Relic Logs, search:
  - `pipeline_id = 'retail_data_pipeline'`
  - `run_id = '<run_id_from_console>'`
  - `tenant_id = 'tenant_001'`
5. Verify stage events: Bronze/Silver/Gold start/end and pipeline completion.
6. In New Relic Metrics, verify durations and record-count metrics.

### Controlled failure test

Use a temporary bad source configuration (for example invalid `FASTAPI_BASE_URL`) and run once.

Expected:

- Pipeline emits `ERROR` logs.
- `PIPELINE_FAILURE` and stage failure events visible.
- Event contains `pipeline_id`, `run_id`, `tenant_id`, `stage`, `dataset`, and `error_type`.

Restore valid configuration immediately after test.

### Data-quality monitoring test

Run with existing invalid Silver scenarios already present in test data (for example invalid price rule violations).

Expected:

- Invalid rows quarantined.
- `DATA_QUALITY_FAILURE` and `QUARANTINE_RECORDS` events appear.
- `silver_invalid_records` and related quality metrics increase.

## 25. Non-Blocking Telemetry Guarantee

Telemetry export failures do not fail Spark data processing. If OTLP export is unavailable, pipeline data processing can still succeed while observability logs a `TELEMETRY_EXPORT_FAILURE` warning.

## 17. Future AWS architecture

This MVP is intentionally limited to FastAPI + PySpark + S3 + Parquet. The
code is structured (clear layer boundaries, config-driven S3 paths, no
hardcoded bucket names) so it can evolve without a redesign to:

```
FastAPI -> AWS ingestion service -> Amazon S3 -> AWS Glue Data Catalog
   -> Apache Spark / EMR / AWS Glue -> Bronze -> Silver -> Gold
   -> Amazon Athena / Redshift / BI / ML
```

## Project structure

```
retail-spark-pipeline/
├── src/
│   ├── config/config.py            # env + pipeline_config.yaml loader
│   ├── ingestion/
│   │   ├── api_client.py           # FastAPI HTTP client (X-Tenant-ID)
│   │   ├── paginator.py            # walks limit/offset until has_more=false
│   │   └── bronze_ingestion.py     # FastAPI -> Bronze DataFrame + metadata
│   ├── bronze/bronze_writer.py     # partitioned Parquet writer
│   ├── silver/
│   │   ├── schema.py                # explicit StructTypes per dataset
│   │   ├── validation.py            # required fields + business rules
│   │   ├── cleansing.py             # normalization + dedup
│   │   └── silver_transform.py      # Bronze -> Silver + quarantine orchestration
│   ├── gold/
│   │   ├── pricing.py               # gold_pricing (documented formulas)
│   │   ├── enrichment.py            # promotion/inventory/sales enrichment
│   │   └── gold_transform.py        # Silver -> Gold orchestration + validation
│   ├── quality/
│   │   ├── metrics.py               # Silver quality metrics
│   │   └── quality_checks.py        # Gold validation + tenant-isolation guard
│   ├── utils/
│   │   ├── logger.py, run_id.py, spark_session.py, s3_log_writer.py
│   └── main.py                      # pipeline orchestrator
├── tests/                           # see section 15
├── config/pipeline_config.yaml       # datasets, endpoints, tenants (non-secret)
├── .env.example
├── requirements.txt
├── run_pipeline.py                   # CLI entry point
└── README.md
```
