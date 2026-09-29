You are an expert DevOps, Data Engineering and Observability engineer.

I already have a working multi-tenant retail data pipeline that performs:

FastAPI Source Systems
        ↓
Apache Spark / PySpark
        ↓
AWS S3 Bronze
        ↓
PySpark Validation / Cleansing
        ↓
AWS S3 Silver
        ↓
PySpark Transformation / Enrichment
        ↓
AWS S3 Gold
        ↓
Pricing / Analytics


IMPORTANT:

The Bronze, Silver and Gold layers are ALREADY populated in AWS S3.

DO NOT redesign or rewrite the existing data pipeline.

DO NOT change the existing Bronze, Silver or Gold business logic.

Your task is to add New Relic observability on top of the existing
Apache Spark pipeline.

The objective is:

Apache Spark Pipeline
        |
        | logs + metrics
        ▼
OpenTelemetry / New Relic integration
        |
        ▼
New Relic Cloud
        |
        ├── Logs
        ├── Metrics
        ├── Pipeline monitoring
        ├── Data-quality monitoring
        └── Dashboards


============================================================
1. PRIMARY OBJECTIVES
============================================================

Implement two major objectives:

A. Create/configure a New Relic cloud account and trial/free
   environment.

B. Publish Apache Spark pipeline logs and metrics to New Relic.


The final system must allow me to monitor:

- pipeline execution
- Bronze ingestion
- Silver validation
- Silver data quality
- Gold transformation
- Gold validation
- record counts
- invalid record counts
- processing duration
- failures
- S3 read/write status
- tenant-level pipeline execution
- run-level pipeline execution


============================================================
2. IMPORTANT CONSTRAINT
============================================================

The following has already been completed:

FastAPI source system
        ↓
Spark ingestion
        ↓
S3 Bronze
        ↓
Spark Silver
        ↓
S3 Silver
        ↓
Spark Gold
        ↓
S3 Gold


Do NOT rebuild these components.

Do NOT recreate:

- FastAPI
- Bronze ingestion
- Silver transformation
- Gold transformation
- S3 data lake


Only instrument the existing pipeline.


============================================================
3. NEW RELIC ACCOUNT SETUP
============================================================

Set up a New Relic cloud account using the current New Relic
signup/onboarding flow.

Use the available free/trial option applicable to the account.

IMPORTANT:

Do not automate creation of a New Relic account by storing
personal credentials or payment information in code.

The user must perform account signup/authentication manually.

The implementation should provide clear step-by-step instructions
for:

1. Creating/logging into the New Relic account.
2. Selecting the appropriate New Relic region.
3. Creating/selecting the New Relic account.
4. Obtaining the required ingest/license key.
5. Configuring the New Relic region.
6. Configuring telemetry ingestion.


Do not hardcode the New Relic license/ingest key.


============================================================
4. NEW RELIC REGION
============================================================

The implementation must support New Relic regions.

Make the region configurable.

Example:

NEW_RELIC_REGION=us

or:

NEW_RELIC_REGION=eu

Do not hardcode a specific region unless explicitly configured
by the user.

Use the appropriate New Relic OTLP endpoint for the selected
region.


============================================================
5. NEW RELIC AUTHENTICATION
============================================================

Use environment variables.

Example:

NEW_RELIC_LICENSE_KEY=<secret>
NEW_RELIC_REGION=us


Never place:

NEW_RELIC_LICENSE_KEY

inside:

- Python source code
- Git repository
- README
- Dockerfile
- YAML configuration committed to Git


Add:

.env

to:

.gitignore


Provide:

.env.example


Example:

NEW_RELIC_LICENSE_KEY=
NEW_RELIC_REGION=us

PIPELINE_ID=retail_data_pipeline

S3_BUCKET=retail-data-lake-dev


============================================================
6. TELEMETRY TRANSPORT
============================================================

Prefer OpenTelemetry with OTLP for telemetry delivery to
New Relic.

Use New Relic's supported OTLP ingestion mechanism.

The implementation must support:

LOGS
METRICS


Do not send sensitive AWS credentials or secrets as telemetry
attributes.


============================================================
7. OBSERVABILITY ARCHITECTURE
============================================================

Implement:

                     APACHE SPARK
                          |
              ┌───────────┴───────────┐
              │                       │
              ▼                       ▼
          Pipeline Logs          Pipeline Metrics
              │                       │
              └───────────┬───────────┘
                          │
                          ▼
                  OpenTelemetry
                          │
                         OTLP
                          │
                          ▼
                  ┌──────────────┐
                  │  NEW RELIC   │
                  │    CLOUD     │
                  └──────┬───────┘
                         │
             ┌───────────┼───────────┐
             ▼           ▼           ▼
           Logs       Metrics    Dashboards


============================================================
8. LOGGING OBJECTIVE
============================================================

Publish important Apache Spark pipeline logs to New Relic.

Logs should cover:

1. Pipeline started
2. Pipeline completed
3. Pipeline failed
4. Bronze started
5. Bronze completed
6. Bronze failed
7. Silver started
8. Silver completed
9. Silver failed
10. Gold started
11. Gold completed
12. Gold failed
13. API ingestion errors
14. S3 read errors
15. S3 write errors
16. Validation failures
17. Quarantine events
18. Data-quality failures


============================================================
9. STRUCTURED LOG FORMAT
============================================================

Do NOT send only plain-text logs.

Use structured logs.

Every important pipeline log should contain:

timestamp
level
message
pipeline_id
run_id
tenant_id
stage
dataset
status


Example:

{
    "timestamp": "2026-09-25T16:30:00Z",
    "level": "INFO",
    "message": "Silver transformation completed",

    "pipeline_id": "retail_data_pipeline",
    "run_id": "20260925_163000_a83f21",
    "tenant_id": "tenant_001",

    "stage": "silver",
    "dataset": "products",

    "status": "SUCCESS",

    "input_records": 50,
    "valid_records": 47,
    "invalid_records": 3,
    "processing_time_seconds": 8.4
}


============================================================
10. REQUIRED LOG EVENTS
============================================================

Create structured events for:

PIPELINE_START

PIPELINE_END

PIPELINE_FAILURE

BRONZE_START

BRONZE_END

BRONZE_FAILURE

SILVER_START

SILVER_END

SILVER_FAILURE

GOLD_START

GOLD_END

GOLD_FAILURE

DATA_QUALITY_FAILURE

S3_READ_FAILURE

S3_WRITE_FAILURE

API_FAILURE

QUARANTINE_RECORDS


Each event should contain enough metadata to diagnose the
pipeline execution.


============================================================
11. REQUIRED PIPELINE ATTRIBUTES
============================================================

Always preserve:

pipeline_id
run_id
tenant_id


Additional useful attributes:

stage
dataset
source_system
status
environment
processing_date


Example:

pipeline_id:
retail_data_pipeline

run_id:
20260925_163000_a83f21

tenant_id:
tenant_001

stage:
silver

dataset:
products

status:
SUCCESS

environment:
dev


============================================================
12. METRICS
============================================================

Publish custom metrics to New Relic.

At minimum implement:

1. pipeline_run_count

2. pipeline_success_count

3. pipeline_failure_count

4. pipeline_duration_seconds

5. bronze_records_ingested

6. bronze_records_written

7. silver_input_records

8. silver_valid_records

9. silver_invalid_records

10. silver_duplicate_records

11. silver_quarantine_records

12. gold_input_records

13. gold_output_records

14. gold_validation_failures

15. s3_read_duration_seconds

16. s3_write_duration_seconds

17. api_request_count

18. api_error_count

19. api_request_duration_seconds


============================================================
13. METRIC ATTRIBUTES
============================================================

Metrics should contain useful dimensions.

Recommended attributes:

pipeline_id
run_id
tenant_id
stage
dataset
environment


Example:

metric:

silver_invalid_records


attributes:

tenant_id=tenant_001
dataset=products
stage=silver
environment=dev


Avoid extremely high-cardinality attributes where they are not
useful.

Do not use unrestricted:

record_id
order_id
product_id

as metric dimensions unless there is a specific reason.


============================================================
14. PIPELINE DURATION
============================================================

Measure:

Total pipeline duration

Bronze duration

Silver duration

Gold duration


Example:

pipeline_duration_seconds = 125.4

bronze_duration_seconds = 30.1

silver_duration_seconds = 42.5

gold_duration_seconds = 52.8


Send these metrics to New Relic.


============================================================
15. DATA QUALITY METRICS
============================================================

Expose the existing Silver data-quality metrics to New Relic.

Metrics:

input_record_count
valid_record_count
invalid_record_count
duplicate_record_count
null_violation_count
business_rule_violation_count
referential_integrity_failure_count
quarantine_record_count


For example:

tenant_001
products
Silver

input = 50
valid = 47
invalid = 3


New Relic should allow me to query these metrics by:

tenant_id
dataset
stage
pipeline_id


============================================================
16. BRONZE OBSERVABILITY
============================================================

Monitor Bronze ingestion.

Capture:

dataset
tenant_id
run_id

records_received

records_written

API_duration

S3_write_duration

status


Example:

Bronze products:

records_received = 50
records_written = 50
duration = 5.2 seconds
status = SUCCESS


============================================================
17. SILVER OBSERVABILITY
============================================================

Monitor:

records_read_from_bronze

records_validated

records_valid

records_invalid

duplicates

quarantined_records

validation_duration

S3_write_duration

status


Example:

Silver products:

input = 50
valid = 47
invalid = 3
duplicates = 1
quarantine = 3


============================================================
18. GOLD OBSERVABILITY
============================================================

Monitor:

input_records

output_records

join_failures

pricing_validation_failures

null_product_ids

duplicate_business_keys

negative_final_prices

transformation_duration

S3_write_duration

status


Example:

Gold pricing:

input = 47
output = 47
validation_failures = 0
status = SUCCESS


============================================================
19. ERROR OBSERVABILITY
============================================================

When an error occurs, send a structured error log.

Example:

{
    "timestamp": "...",

    "level": "ERROR",

    "message": "Failed to write Silver dataset",

    "pipeline_id": "retail_data_pipeline",

    "run_id": "20260925_163000_a83f21",

    "tenant_id": "tenant_001",

    "stage": "silver",

    "dataset": "products",

    "error_type": "S3_WRITE_ERROR",

    "status": "FAILED"
}


Do not send secrets, credentials or sensitive payloads.


============================================================
20. NEW RELIC DASHBOARD
============================================================

Create a New Relic dashboard for:

Retail Data Pipeline Monitoring


The dashboard should show:

------------------------------------------------
PIPELINE OVERVIEW
------------------------------------------------

- Total pipeline runs
- Successful runs
- Failed runs
- Average pipeline duration
- Latest pipeline status


------------------------------------------------
BRONZE
------------------------------------------------

- Records ingested
- Records written
- Ingestion duration
- API errors
- S3 write failures


------------------------------------------------
SILVER
------------------------------------------------

- Records processed
- Valid records
- Invalid records
- Duplicate records
- Quarantined records
- Data-quality failure count


------------------------------------------------
GOLD
------------------------------------------------

- Gold input records
- Gold output records
- Gold validation failures
- Pricing records
- Product-sales records


------------------------------------------------
TENANT MONITORING
------------------------------------------------

Show metrics by:

tenant_id


For example:

tenant_001
tenant_002
tenant_003


------------------------------------------------
PIPELINE HEALTH
------------------------------------------------

Show:

SUCCESS
FAILED
RUNNING


and pipeline duration.


============================================================
21. NEW RELIC QUERIES
============================================================

Create example NRQL queries.

Examples should cover:

1. Recent pipeline runs

2. Pipeline failures

3. Silver invalid records

4. Gold validation failures

5. Pipeline duration

6. Records processed

7. Tenant-level metrics

8. Bronze ingestion failures

9. API failures

10. S3 failures


Use the current New Relic event/metric data model appropriate
to the telemetry method actually implemented.

Do not invent unsupported event names.


============================================================
22. PIPELINE FAILURE ALERT
============================================================

Create an alert condition for:

Pipeline failure


Conceptually:

If a pipeline execution fails:

→ New Relic detects failure
→ alert condition triggers


The implementation should document how to create/configure the
alert using the current New Relic UI/API.


Do not hardcode notification destinations.

Leave notification configuration to the user.


============================================================
23. DATA QUALITY ALERTS
============================================================

Create recommended alert conditions for:

1. High Silver invalid-record rate

2. High duplicate rate

3. Gold validation failure

4. Pipeline duration anomaly

5. Pipeline failure

6. S3 write failure

7. API failure rate


Example condition:

invalid_records / input_records > 10%


The threshold must be configurable.

Example:

SILVER_INVALID_RATE_THRESHOLD=0.10


============================================================
24. OBSERVABILITY CONFIGURATION
============================================================

Create:

observability/
    logging_config.py
    metrics.py
    newrelic_exporter.py
    telemetry.py


Keep New Relic-specific code separate from the core Spark
transformation logic.


The existing pipeline should conceptually call:

start_pipeline()

record_metric(...)

log_event(...)

record_stage_start(...)

record_stage_end(...)

record_quality_metrics(...)

record_pipeline_failure(...)


This prevents New Relic code from being tightly coupled to
Bronze/Silver/Gold transformations.


============================================================
25. ENVIRONMENT CONFIGURATION
============================================================

Update .env.example:

AWS_REGION=ap-south-1

S3_BUCKET=retail-data-lake-dev

FASTAPI_BASE_URL=http://localhost:8000

PIPELINE_ID=retail_data_pipeline

ENVIRONMENT=dev

NEW_RELIC_LICENSE_KEY=

NEW_RELIC_REGION=us

NEW_RELIC_SERVICE_NAME=retail-spark-pipeline


Never commit the real license key.


============================================================
26. SERVICE NAME
============================================================

Use:

retail-spark-pipeline


as the New Relic service/resource name.

Optionally differentiate environments:

retail-spark-pipeline-dev

retail-spark-pipeline-test

retail-spark-pipeline-prod


The environment must be configurable.


============================================================
27. OPEN TELEMETRY RESOURCE ATTRIBUTES
============================================================

Configure OpenTelemetry resource attributes such as:

service.name
service.version
deployment.environment


Also include:

pipeline_id


Where appropriate, include:

tenant_id

as an event/metric attribute.

Be careful not to create excessive metric cardinality.


============================================================
28. DO NOT BREAK SPARK PROCESSING
============================================================

New Relic observability must be non-blocking wherever practical.

If telemetry delivery temporarily fails:

the main data pipeline should not automatically fail simply
because New Relic telemetry could not be delivered.

Log telemetry-export failures separately.

Example:

Spark pipeline:
SUCCESS

New Relic telemetry:
PARTIAL_FAILURE


Do not make New Relic the dependency that determines whether
Bronze/Silver/Gold data processing succeeds.


============================================================
29. LOG VOLUME CONTROL
============================================================

Do NOT send every Spark internal log line to New Relic.

Send:

- pipeline-level logs
- stage-level logs
- dataset-level logs
- data-quality logs
- errors
- important warnings
- execution summaries


Avoid sending massive raw Spark executor logs unless explicitly
required.


============================================================
30. SENSITIVE DATA
============================================================

Never send to New Relic:

AWS access keys
AWS secret keys
AWS session tokens
New Relic license keys
customer PII
passwords
authorization tokens
API credentials
full raw API responses


Only send operational metadata and aggregate metrics.


============================================================
31. VALIDATION
============================================================

After implementation, execute the existing pipeline:

FastAPI
   ↓
S3 Bronze
   ↓
S3 Silver
   ↓
S3 Gold


Then verify:

1. Pipeline completes successfully.

2. Bronze remains unchanged.

3. Silver remains unchanged.

4. Gold remains unchanged.

5. Logs appear in New Relic.

6. Metrics appear in New Relic.

7. pipeline_id is searchable.

8. run_id is searchable.

9. tenant_id is available.

10. stage is available.

11. dataset is available.

12. pipeline failures are visible.

13. data-quality failures are visible.


============================================================
32. NEW RELIC VERIFICATION
============================================================

Provide a verification procedure.

The user should be able to:

1. Start FastAPI.

2. Start the Spark pipeline.

3. Wait for Bronze/Silver/Gold completion.

4. Open New Relic.

5. Navigate to Logs.

6. Search for:

pipeline_id = retail_data_pipeline


7. Search by:

run_id


8. Filter:

tenant_id = tenant_001


9. Verify:

Bronze logs

Silver logs

Gold logs


10. Open Metrics and verify:

pipeline duration

record counts

invalid records

Gold output records


============================================================
33. TEST RUN
============================================================

Create a small test execution.

Example:

tenant:

tenant_001

pipeline:

retail_data_pipeline

mode:

full


The test must generate:

Pipeline start
Bronze completion
Silver completion
Gold completion
Pipeline completion


and corresponding metrics.


============================================================
34. FAILURE TEST
============================================================

Create a controlled failure test.

For example:

temporarily provide an invalid S3 path or invalid source
configuration.

Expected:

Spark pipeline logs an ERROR.

New Relic receives the error event.

Pipeline status becomes FAILED.

The error contains:

pipeline_id
run_id
tenant_id
stage
dataset
error_type


Do not expose credentials.


============================================================
35. DATA QUALITY TEST
============================================================

Use an existing intentionally invalid Silver record.

For example:

negative product price


Expected:

Silver identifies the invalid record.

Record goes to quarantine.

Silver quality metric increases.

New Relic receives:

invalid_record_count

and a corresponding structured log.


============================================================
36. README
============================================================

Update README.md with:

1. New Relic architecture
2. Account setup
3. New Relic region selection
4. License/ingest key setup
5. Environment variables
6. OpenTelemetry configuration
7. Log configuration
8. Metric configuration
9. Dashboard setup
10. NRQL queries
11. Alert setup
12. Pipeline verification
13. Failure testing
14. Data-quality monitoring
15. Security considerations
16. Troubleshooting


============================================================
37. FINAL ARCHITECTURE
============================================================

The final architecture should be documented as:

                    FASTAPI SOURCES
                          |
                          ▼
                    PYSPARK PIPELINE
                          |
          ┌───────────────┼────────────────┐
          │               │                │
          ▼               ▼                ▼
       BRONZE           SILVER            GOLD
          |               |                |
          └───────────────┼────────────────┘
                          |
                          ▼
                    S3 DATA LAKE


                     PYSPARK
                        |
             ┌──────────┴──────────┐
             │                     │
             ▼                     ▼
          LOGGING               METRICS
             │                     │
             └──────────┬──────────┘
                        ▼
                  OPENTELEMETRY
                        |
                       OTLP
                        |
                        ▼
                ┌───────────────┐
                │  NEW RELIC    │
                │     CLOUD     │
                └───────┬───────┘
                        |
          ┌─────────────┼─────────────┐
          ▼             ▼             ▼
        Logs          Metrics      Dashboard
          |
          ▼
      Alerts


============================================================
38. IMPORTANT CONSTRAINTS
============================================================

Do NOT:

- recreate the FastAPI server
- recreate Bronze/Silver/Gold
- change existing business calculations
- change S3 data structures unnecessarily
- move data out of S3
- hardcode New Relic credentials
- hardcode AWS credentials
- send PII
- send raw API responses
- send every Spark executor log
- make New Relic telemetry failure fail the data pipeline
- replace Spark with Pandas


The primary objective is OBSERVABILITY of the existing
Apache Spark retail data pipeline.


============================================================
39. FINAL DELIVERABLES
============================================================

Deliver:

1. New Relic setup instructions
2. OpenTelemetry configuration
3. New Relic integration code
4. Structured logging implementation
5. Custom metrics implementation
6. Environment configuration
7. Dashboard configuration/instructions
8. NRQL queries
9. Alert configuration/instructions
10. Verification procedure
11. Failure test
12. Data-quality monitoring test
13. Updated README
14. requirements.txt updates
15. .env.example
16. .gitignore updates


============================================================
40. FINAL SUCCESS CRITERIA
============================================================

The implementation is successful when:

FASTAPI
   ↓
PYSPARK
   ↓
S3 BRONZE
   ↓
S3 SILVER
   ↓
S3 GOLD

continues to work exactly as before,

AND:

PYSPARK
   ↓
OpenTelemetry / OTLP
   ↓
NEW RELIC

provides:

✓ Pipeline logs
✓ Pipeline metrics
✓ Bronze metrics
✓ Silver data-quality metrics
✓ Gold transformation metrics
✓ Pipeline duration
✓ Pipeline failures
✓ S3 errors
✓ API errors
✓ Tenant-level visibility
✓ Run-level traceability
✓ Dashboard
✓ Alerting


The same:

tenant_id
pipeline_id
run_id

must allow an operator to trace a pipeline execution from
the Spark pipeline into New Relic.


Do not modify the business data-processing behavior merely to
add observability.