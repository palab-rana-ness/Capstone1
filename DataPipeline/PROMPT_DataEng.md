You are an expert AWS Data Engineer and Apache Spark / PySpark developer.

Build an end-to-end, production-style MVP retail data pipeline using:

- FastAPI as the application/source layer
- Apache Spark / PySpark as the processing engine
- AWS S3 as the data lake storage
- Parquet as the storage format
- Bronze, Silver and Gold layers stored in S3

DO NOT use the local filesystem as the persistent storage for
Bronze, Silver or Gold.

The target architecture is:

                    ┌─────────────────────────┐
                    │   Retail FastAPI APIs   │
                    │                         │
                    │ Products                │
                    │ Sales                   │
                    │ Inventory               │
                    │ Promotions              │
                    │ Suppliers               │
                    └────────────┬────────────┘
                                 │
                                 │ HTTP / JSON
                                 ▼
                    ┌─────────────────────────┐
                    │   PySpark Ingestion     │
                    └────────────┬────────────┘
                                 │
                                 ▼
              ┌────────────────────────────────────┐
              │          AWS S3 DATA LAKE          │
              │                                    │
              │  ┌──────────┐                      │
              │  │  BRONZE  │                      │
              │  │ Near Raw │                      │
              │  └────┬─────┘                      │
              │       │                             │
              │       ▼                             │
              │  ┌──────────┐                       │
              │  │  SILVER  │                       │
              │  │  Clean   │                       │
              │  └────┬─────┘                       │
              │       │                             │
              │       ▼                             │
              │  ┌──────────┐                       │
              │  │   GOLD   │                       │
              │  │ Business │                       │
              │  └──────────┘                       │
              └────────────────────────────────────┘
                                 │
                                 ▼
                       Pricing / Analytics


============================================================
1. PRIMARY OBJECTIVE
============================================================

Build a multi-tenant retail data pipeline that performs:

A. FastAPI Application → AWS S3 Bronze

B. AWS S3 Bronze → AWS S3 Silver

C. AWS S3 Silver → AWS S3 Gold


Apache Spark / PySpark must be used for:

- ingestion
- validation
- cleansing
- transformation
- enrichment
- aggregation
- writing Parquet datasets


The three layers must have clearly separated responsibilities.


============================================================
2. DATA FLOW
============================================================

The final data flow must be:

Sources
   ↓
FastAPI APIs
   ↓
PySpark Ingestion
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

Bronze:
Source data remains close to original form.

Silver:
Trusted, clean, standardized data.

Gold:
Business-specific, consumption-ready data.


============================================================
3. EXISTING FASTAPI SOURCE SYSTEM
============================================================

The FastAPI server already exists.

DO NOT recreate or modify the FastAPI server.

Use the existing APIs as the source systems.

The primary source datasets are:

1. products
2. sales
3. inventory
4. promotions
5. suppliers

Supporting datasets:

6. customers
7. stores
8. categories


The FastAPI APIs support:

- X-Tenant-ID
- pagination
- updated_since
- filtering

Use those existing capabilities.


============================================================
4. SOURCE API ENDPOINTS
============================================================

Use:

GET /api/v1/products

GET /api/v1/sales/orders

GET /api/v1/sales/orders/{order_id}/items

GET /api/v1/sales/transactions

GET /api/v1/inventory

GET /api/v1/promotions

GET /api/v1/suppliers

GET /api/v1/customers

GET /api/v1/stores

GET /api/v1/categories


The source API uses:

X-Tenant-ID


Example:

X-Tenant-ID: tenant_001


The API supports:

limit
offset
updated_since


Use pagination rather than assuming the entire dataset is
returned in one response.


============================================================
5. AWS S3 DATA LAKE
============================================================

Use AWS S3 as the persistent storage layer.

The pipeline must write:

Bronze → S3
Silver → S3
Gold → S3


Do NOT use:

- local folders as the final storage
- PostgreSQL
- MySQL
- MongoDB
- Redis


The local machine may be used for:

- Spark execution
- temporary files
- logs during development
- configuration

But all actual data lake datasets must be stored in S3.


============================================================
6. S3 BUCKET
============================================================

Make the S3 bucket configurable.

Example:

S3_BUCKET=retail-data-lake-dev


Do NOT hardcode the bucket name throughout the code.

Use configuration such as:

AWS_REGION
S3_BUCKET
FASTAPI_BASE_URL
PIPELINE_ID


Example:

AWS_REGION=ap-south-1

S3_BUCKET=retail-data-lake-dev

FASTAPI_BASE_URL=http://localhost:8000

PIPELINE_ID=retail_data_pipeline


============================================================
7. S3 DATA LAKE STRUCTURE
============================================================

Use the following logical structure:

s3://<bucket>/

    bronze/
        products/
        sales/
        inventory/
        promotions/
        suppliers/
        customers/
        stores/
        categories/

    silver/
        products/
        sales/
        inventory/
        promotions/
        suppliers/
        customers/
        stores/
        categories/

    gold/
        pricing/
        product_sales/

    quarantine/

        products/
        sales/
        inventory/
        promotions/
        suppliers/

    logs/

        ingestion/
        quality/
        pipeline/


Use Parquet for Bronze, Silver and Gold.


============================================================
8. PARTITIONING STRATEGY
============================================================

Use S3 partitioning to support efficient data processing.

At minimum partition by:

tenant_id

and ingestion/business date where appropriate.

Example:

s3://retail-data-lake-dev/bronze/products/
    tenant_id=tenant_001/
    ingestion_date=2026-09-25/


Example:

s3://retail-data-lake-dev/silver/products/
    tenant_id=tenant_001/
    ingestion_date=2026-09-25/


For Gold, use appropriate business partitions.

For example:

s3://retail-data-lake-dev/gold/pricing/
    tenant_id=tenant_001/
    business_date=2026-09-25/


Do not create excessive small partitions.


============================================================
9. MULTI-TENANCY
============================================================

Support:

tenant_001
tenant_002
tenant_003


Pipeline command:

python run_pipeline.py \
    --tenant-id tenant_001


Also support:

python run_pipeline.py \
    --tenant-id all


Every record in Bronze, Silver and Gold MUST retain:

tenant_id


All joins must use tenant_id as part of the join condition
where appropriate.

NEVER perform:

products.product_id = inventory.product_id


alone.

Instead use:

products.tenant_id = inventory.tenant_id
AND
products.product_id = inventory.product_id


This is mandatory for all cross-dataset joins.


============================================================
10. PIPELINE TRACEABILITY
============================================================

Every record must retain:

tenant_id
pipeline_id
run_id


Also retain:

source_system
ingestion_timestamp


Example:

tenant_id:
tenant_001

pipeline_id:
retail_data_pipeline

run_id:
20260925_143015_a83f21

source_system:
product_api

ingestion_timestamp:
2026-09-25T14:30:15Z


These fields must survive:

Bronze
→ Silver
→ Gold


A downstream user must be able to trace any Gold record back
to its pipeline execution.


============================================================
11. RUN ID
============================================================

Generate a unique run_id once at the beginning of the pipeline.

Example:

20260925_143015_a83f21


The same run_id must be used for:

Bronze ingestion
Silver processing
Gold processing
Quality metrics
Pipeline logs


============================================================
12. TECHNOLOGY
============================================================

Use:

Python 3.11+
Apache Spark 3.x
PySpark
AWS S3
Hadoop S3A connector
Parquet
boto3 where required
requests or httpx
pytest


Use Spark's S3A filesystem:

s3a://


Example:

s3a://retail-data-lake-dev/bronze/products/


Do NOT use:

s3://

for Spark filesystem operations if S3A is required by the
configured Spark environment.

Configure Spark to use the appropriate Hadoop AWS / AWS SDK
dependencies compatible with the selected Spark version.


============================================================
13. AWS CREDENTIAL MANAGEMENT
============================================================

NEVER hardcode:

AWS access key
AWS secret key
AWS session token


Support standard AWS credential mechanisms.

Prefer:

AWS IAM Role

or:

AWS CLI configured credentials

or:

environment variables

or:

AWS profile


The code should work with:

AWS_PROFILE

when running locally if configured.


For production-like execution, document the use of an IAM role
with minimum required S3 permissions.


============================================================
14. REQUIRED AWS S3 PERMISSIONS
============================================================

Document the minimum permissions needed.

The Spark execution identity should have permissions for:

s3:ListBucket

s3:GetObject

s3:PutObject

s3:DeleteObject

where deletion is actually required.

Do not request unrestricted:

s3:*

unless explicitly necessary.


============================================================
15. PROJECT STRUCTURE
============================================================

Create:

retail-spark-pipeline/

│
├── src/
│   ├── config/
│   │   └── config.py
│   │
│   ├── ingestion/
│   │   ├── api_client.py
│   │   ├── paginator.py
│   │   └── bronze_ingestion.py
│   │
│   ├── bronze/
│   │   └── bronze_writer.py
│   │
│   ├── silver/
│   │   ├── schema.py
│   │   ├── validation.py
│   │   ├── cleansing.py
│   │   └── silver_transform.py
│   │
│   ├── gold/
│   │   ├── pricing.py
│   │   ├── enrichment.py
│   │   └── gold_transform.py
│   │
│   ├── quality/
│   │   ├── metrics.py
│   │   └── quality_checks.py
│   │
│   ├── utils/
│   │   ├── logger.py
│   │   ├── run_id.py
│   │   └── spark_session.py
│   │
│   └── main.py
│
├── tests/
│
├── config/
│   └── pipeline_config.yaml
│
├── .env.example
├── requirements.txt
├── README.md
└── run_pipeline.py


============================================================
16. STAGE A — FASTAPI → S3 BRONZE
============================================================

Implement:

FastAPI
   ↓
HTTP JSON
   ↓
PySpark ingestion
   ↓
S3 Bronze


The ingestion process must:

1. Read tenant_id
2. Generate pipeline_id
3. Generate run_id
4. Call FastAPI
5. Handle pagination
6. Retrieve all records
7. Preserve source fields
8. Add metadata
9. Write Parquet to S3
10. Record metrics


============================================================
17. BRONZE RESPONSIBILITY
============================================================

Bronze must remain close to source data.

Do NOT perform business calculations.

Do NOT calculate:

gross_amount
net_price
margin
profit
promotion_effectiveness
revenue


Bronze may perform only minimal transformations required for:

- serialization
- metadata
- ingestion timestamp
- source identification
- basic schema compatibility


============================================================
18. BRONZE METADATA
============================================================

Every Bronze record must contain:

tenant_id
pipeline_id
run_id
source_system
ingestion_timestamp


Example:

{
    "product_id": "prod_001",
    "sku": "SKU001",
    "product_name": "Laptop",
    "unit_price": 75000,

    "tenant_id": "tenant_001",
    "pipeline_id": "retail_data_pipeline",
    "run_id": "20260925_143015_a83f21",
    "source_system": "product_api",
    "ingestion_timestamp": "2026-09-25T14:30:15Z"
}


============================================================
19. BRONZE S3 PATH
============================================================

Example:

s3a://retail-data-lake-dev/bronze/products/
tenant_id=tenant_001/
ingestion_date=2026-09-25/


Similarly:

s3a://retail-data-lake-dev/bronze/sales/
tenant_id=tenant_001/
ingestion_date=2026-09-25/


s3a://retail-data-lake-dev/bronze/inventory/
tenant_id=tenant_001/
ingestion_date=2026-09-25/


s3a://retail-data-lake-dev/bronze/promotions/
tenant_id=tenant_001/
ingestion_date=2026-09-25/


s3a://retail-data-lake-dev/bronze/suppliers/
tenant_id=tenant_001/
ingestion_date=2026-09-25/


============================================================
20. BRONZE FORMAT
============================================================

Write:

Parquet


Use:

df.write \
  .mode(...) \
  .partitionBy("tenant_id", "ingestion_date") \
  .parquet("s3a://...")


Choose the write mode carefully to avoid duplicate data during
pipeline reruns.


============================================================
21. INGESTION LOGGING
============================================================

Write ingestion logs to S3.

Example:

s3a://retail-data-lake-dev/logs/ingestion/


Each log must contain:

pipeline_id
run_id
tenant_id
dataset
source_system
start_time
end_time
records_received
records_written
status
error_message


Example:

{
    "pipeline_id": "retail_data_pipeline",
    "run_id": "20260925_143015_a83f21",
    "tenant_id": "tenant_001",
    "dataset": "products",
    "source_system": "product_api",
    "records_received": 50,
    "records_written": 50,
    "status": "SUCCESS"
}


============================================================
22. INCREMENTAL INGESTION
============================================================

Support:

FULL

and:

INCREMENTAL


Full:

python run_pipeline.py \
    --tenant-id tenant_001 \
    --mode full


Incremental:

python run_pipeline.py \
    --tenant-id tenant_001 \
    --mode incremental \
    --updated-since 2026-09-24T00:00:00Z


Use the FastAPI:

updated_since

parameter.


Example:

GET /api/v1/products?updated_since=...


Do not implement a complex CDC framework for this MVP.


============================================================
23. STAGE B — S3 BRONZE → S3 SILVER
============================================================

Read Bronze Parquet using PySpark:

spark.read.parquet(
    "s3a://retail-data-lake-dev/bronze/..."
)


Apply:

1. Explicit schemas
2. Type standardization
3. Null validation
4. Duplicate detection
5. Duplicate handling
6. Business rule validation
7. Timestamp standardization
8. Categorical normalization
9. Referential integrity validation


Write valid data to:

s3a://retail-data-lake-dev/silver/


============================================================
24. SILVER PURPOSE
============================================================

Silver is the trusted operational/analytical clean layer.

Silver must contain:

- clean records
- standardized types
- standardized categories
- valid business fields
- valid relationships
- traceability metadata


Silver becomes the main source for all Gold transformations.


============================================================
25. SILVER SCHEMAS
============================================================

Define explicit PySpark schemas.

Do not rely exclusively on schema inference.

Example:

product_id → StringType
tenant_id → StringType
unit_price → DecimalType
cost_price → DecimalType
tax_rate → DecimalType
created_at → TimestampType
updated_at → TimestampType


Define schemas for:

products
sales
sales_items
inventory
promotions
promotion_products
suppliers
customers
stores
categories


============================================================
26. SILVER REQUIRED-FIELD VALIDATION
============================================================

Products:

product_id
tenant_id
sku
product_name
supplier_id
unit_price
cost_price


Sales:

order_id
tenant_id
order_item_id
product_id
quantity
unit_price


Inventory:

inventory_id
tenant_id
product_id
location_id
quantity_on_hand


Promotions:

promotion_id
tenant_id
promotion_code
start_date
end_date
discount_type
discount_value


Suppliers:

supplier_id
tenant_id
supplier_code
supplier_name


Invalid records must not enter trusted Silver.


============================================================
27. QUARANTINE
============================================================

Invalid records must be written to:

s3a://retail-data-lake-dev/quarantine/


Example:

quarantine/products/
quarantine/sales/
quarantine/inventory/
quarantine/promotions/
quarantine/suppliers/


Each quarantined record should contain:

original fields
tenant_id
pipeline_id
run_id
validation_error
validation_timestamp


Example:

validation_error =
"unit_price must be greater than or equal to zero"


============================================================
28. SILVER DATA QUALITY RULES
============================================================

Products:

unit_price >= 0
cost_price >= 0
tax_rate >= 0
tax_rate <= 100


Sales:

quantity > 0
unit_price >= 0
discount_amount >= 0
tax_amount >= 0
line_total >= 0


Inventory:

quantity_on_hand >= 0
quantity_reserved >= 0
quantity_available >= 0
reorder_level >= 0


Promotions:

discount_value >= 0
start_date <= end_date

Percentage discount <= 100


Suppliers:

rating >= 0
rating <= 5


============================================================
29. DUPLICATE HANDLING
============================================================

Use business keys.

Products:

tenant_id + product_id


Suppliers:

tenant_id + supplier_id


Inventory:

tenant_id + inventory_id


Promotions:

tenant_id + promotion_id


Sales orders:

tenant_id + order_id


Sales items:

tenant_id + order_item_id


Keep the latest valid record where appropriate.

Quarantine duplicate records where useful.


============================================================
30. SILVER QUALITY METRICS
============================================================

Generate:

input_record_count
valid_record_count
invalid_record_count
duplicate_record_count
null_violation_count
business_rule_violation_count
referential_integrity_failure_count
output_record_count


Write metrics to:

s3a://retail-data-lake-dev/logs/quality/


Example:

{
    "dataset": "products",
    "tenant_id": "tenant_001",
    "pipeline_id": "retail_data_pipeline",
    "run_id": "20260925_143015_a83f21",
    "input_record_count": 50,
    "valid_record_count": 47,
    "invalid_record_count": 3,
    "duplicate_record_count": 1,
    "output_record_count": 47,
    "status": "SUCCESS"
}


============================================================
31. SILVER S3 STRUCTURE
============================================================

Use:

s3a://retail-data-lake-dev/silver/products/
    tenant_id=tenant_001/
    processing_date=2026-09-25/


s3a://retail-data-lake-dev/silver/sales/
    tenant_id=tenant_001/
    processing_date=2026-09-25/


s3a://retail-data-lake-dev/silver/inventory/
    tenant_id=tenant_001/
    processing_date=2026-09-25/


s3a://retail-data-lake-dev/silver/promotions/
    tenant_id=tenant_001/
    processing_date=2026-09-25/


============================================================
32. STAGE C — S3 SILVER → S3 GOLD
============================================================

Read:

s3a://retail-data-lake-dev/silver/


Use PySpark to perform:

- joins
- aggregations
- enrichment
- pricing calculations
- inventory calculations
- promotion calculations


Write results to:

s3a://retail-data-lake-dev/gold/


============================================================
33. GOLD PRICING DATASET
============================================================

Create:

gold_pricing


The dataset should contain:

tenant_id
product_id
sku
product_name
category_id
category_name
brand
supplier_id

base_price
cost_price

quantity_sold
inventory_available

promotion_applied
promotion_id
promotion_type
discount_type
discount_value

gross_amount
discount_amount
final_price
net_price

currency

pipeline_id
run_id
transformation_timestamp


============================================================
34. GOLD CALCULATIONS
============================================================

Calculate:

gross_amount

quantity × unit_price


Calculate:

discount_amount


based on the applicable promotion and source discount logic.


Calculate:

final_price / net_price


Document the exact formula.


Ensure:

final_price >= 0


and:

discount_amount <= gross_amount


where applicable.


============================================================
35. PROMOTION ENRICHMENT
============================================================

Join:

Products

with:

PromotionProduct

and:

Promotions


Create:

promotion_applied


Also include:

promotion_id
promotion_type
discount_type
discount_value


A promotion should only be considered applicable when it is
valid for the relevant business date.


============================================================
36. INVENTORY ENRICHMENT
============================================================

Join Products with Inventory.

Create:

inventory_available


If a product exists at multiple locations:

inventory_available =
SUM(quantity_available)


Aggregate at:

tenant_id + product_id


============================================================
37. SALES ENRICHMENT
============================================================

Join:

Sales Orders
+
Sales Order Items
+
Products


Calculate:

quantity_sold
gross_amount
discount_amount
net_amount


All joins must include:

tenant_id


============================================================
38. SECOND GOLD DATASET
============================================================

Create:

gold_product_sales


Fields:

tenant_id
product_id
sku
product_name
category_name

total_quantity_sold
gross_revenue
discount_amount
net_revenue

average_selling_price
inventory_available

pipeline_id
run_id
transformation_timestamp


============================================================
39. GOLD S3 STRUCTURE
============================================================

Create:

s3a://retail-data-lake-dev/gold/pricing/
    tenant_id=tenant_001/
    business_date=2026-09-25/


and:

s3a://retail-data-lake-dev/gold/product_sales/
    tenant_id=tenant_001/
    business_date=2026-09-25/


Use Parquet.


============================================================
40. GOLD VALIDATION
============================================================

Before marking Gold as SUCCESS, verify:

1. tenant_id is not null
2. product_id is not null
3. no duplicate business keys
4. final_price >= 0
5. discount values are valid
6. no cross-tenant joins
7. expected record counts
8. referential integrity
9. pricing calculations are consistent


If a critical Gold validation fails:

Gold status = FAILED


Do not publish an invalid Gold dataset as successful.


============================================================
41. PIPELINE STATUS
============================================================

Maintain:

INGESTION
SILVER
GOLD


Each stage can be:

RUNNING
SUCCESS
FAILED


Example:

{
    "pipeline_id": "retail_data_pipeline",
    "run_id": "20260925_143015_a83f21",
    "tenant_id": "tenant_001",

    "bronze_status": "SUCCESS",
    "silver_status": "SUCCESS",
    "gold_status": "SUCCESS",

    "overall_status": "SUCCESS"
}


Store pipeline logs in:

s3a://retail-data-lake-dev/logs/pipeline/


============================================================
42. S3 WRITE SAFETY
============================================================

The pipeline must be safe to rerun.

Avoid creating duplicate datasets simply because the pipeline
is executed twice.

Use a deterministic strategy involving:

tenant_id
processing_date
run_id


Document whether each stage uses:

append
overwrite
or partition replacement


For the MVP, prefer partition-level replacement or a clearly
documented run-specific output strategy.

Do not blindly overwrite the entire S3 bucket.


============================================================
43. AWS SPARK CONFIGURATION
============================================================

Create a reusable SparkSession.

Configure the S3A filesystem appropriately.

The implementation must account for:

- Hadoop AWS connector
- AWS SDK compatibility
- S3A filesystem
- AWS region
- credentials
- endpoint configuration where required


Use:

spark.hadoop.fs.s3a.impl=
org.apache.hadoop.fs.s3a.S3AFileSystem


Configure credentials through the AWS credential provider
chain rather than hardcoding credentials.


Set:

spark.sql.session.timeZone = UTC


Configure:

spark.sql.shuffle.partitions

appropriately for the MVP.


============================================================
44. REQUIREMENTS.TXT
============================================================

Include the required Python dependencies.

For example:

pyspark
boto3
requests
python-dotenv
pytest


Do not unnecessarily add packages.


The README must explain that Spark's Hadoop AWS/S3A
dependencies must be compatible with the installed Spark/Hadoop
version.


============================================================
45. CONFIGURATION
============================================================

Create:

.env.example


Example:

AWS_REGION=ap-south-1

S3_BUCKET=retail-data-lake-dev

FASTAPI_BASE_URL=http://localhost:8000

PIPELINE_ID=retail_data_pipeline

AWS_PROFILE=default


Do not commit actual AWS credentials.


============================================================
46. FULL EXECUTION
============================================================

Command:

python run_pipeline.py \
    --tenant-id tenant_001 \
    --mode full


Expected flow:

FASTAPI
   ↓
S3 BRONZE
   ↓
S3 SILVER
   ↓
S3 GOLD


Example output:

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
retail-data-lake-dev


[1/3] FASTAPI → S3 BRONZE

Products:   50
Sales:      1000
Inventory:  100
Promotions: 50
Suppliers:  10

Status: SUCCESS


[2/3] S3 BRONZE → S3 SILVER

Products:
Input: 50
Valid: 47
Invalid: 3

Sales:
Input: 1000
Valid: 995
Invalid: 5

Status: SUCCESS


[3/3] S3 SILVER → S3 GOLD

Pricing records: 47
Product sales records: 47

Status: SUCCESS


=========================================
PIPELINE COMPLETED
=========================================

Overall Status: SUCCESS


============================================================
47. AWS S3 FINAL ARCHITECTURE
============================================================

The README must show:

                         FASTAPI
                            │
                            │ HTTP/JSON
                            ▼
                     PySpark Ingestion
                            │
                            ▼
             ┌──────────────────────────┐
             │         AWS S3            │
             │                          │
             │        /bronze            │
             │       Raw-ish Data        │
             │                          │
             │        /silver            │
             │      Clean Data           │
             │                          │
             │         /gold             │
             │    Business Data          │
             │                          │
             │      /quarantine          │
             │      Invalid Data         │
             │                          │
             │         /logs             │
             │      Metrics/Logs         │
             └──────────────────────────┘
                            │
                            ▼
                    Pricing / Analytics


============================================================
48. TESTING
============================================================

Create tests for:

1. FastAPI connectivity
2. API pagination
3. S3 connectivity
4. Bronze write
5. Bronze metadata
6. Tenant isolation
7. Schema validation
8. Null validation
9. Duplicate detection
10. Price validation
11. Quantity validation
12. Discount validation
13. Referential integrity
14. Silver write
15. Gold joins
16. Pricing calculations
17. Inventory calculations
18. Promotion calculations
19. Gold validation
20. Pipeline failure handling


============================================================
49. S3 INTEGRATION TEST
============================================================

Create a test that verifies:

PySpark can write a small test DataFrame to:

s3a://<test-bucket>/test/


and read it back successfully.


Do not run destructive tests against the production bucket.


Use a separate test prefix or bucket.


============================================================
50. TENANT ISOLATION TEST
============================================================

Test:

tenant_001 product

must not join with:

tenant_002 inventory.


Example:

Product:

tenant_id = tenant_001
product_id = prod_001


Inventory:

tenant_id = tenant_002
product_id = prod_001


The Gold dataset must NOT match them.


============================================================
51. README REQUIREMENTS
============================================================

Create a detailed README containing:

1. Architecture
2. AWS S3 structure
3. Source APIs
4. Bronze layer
5. Silver layer
6. Gold layer
7. Multi-tenancy
8. Traceability
9. Data quality
10. S3 partitioning
11. AWS authentication
12. IAM permissions
13. Spark S3A configuration
14. Installation
15. Environment configuration
16. FastAPI startup
17. Full pipeline execution
18. Incremental pipeline execution
19. Testing
20. Troubleshooting
21. Future AWS architecture


============================================================
52. AWS SECURITY REQUIREMENTS
============================================================

Never put AWS credentials directly in:

Python code
YAML files
README
Git repository
Dockerfile


Use:

IAM role

or:

AWS credential provider chain.


Add:

.env

to .gitignore.


Provide:

.env.example

instead.


============================================================
53. IMPORTANT LAYER RULES
============================================================

STRICTLY enforce these rules.


BRONZE:

FastAPI → S3

Allowed:

- ingestion
- serialization
- metadata
- source identification
- ingestion timestamp

Not allowed:

- business calculations
- pricing logic
- revenue calculations
- analytical aggregation


SILVER:

S3 Bronze → PySpark → S3 Silver

Allowed:

- schema standardization
- type conversion
- null checks
- duplicate handling
- validation
- cleansing
- date normalization
- categorical normalization
- referential integrity


GOLD:

S3 Silver → PySpark → S3 Gold

Allowed:

- joins
- aggregation
- pricing calculations
- promotion enrichment
- inventory enrichment
- sales analytics
- business KPIs


============================================================
54. FINAL SUCCESS CRITERIA
============================================================

The implementation is successful only if:

1. FastAPI data is successfully extracted.

2. Data is written to AWS S3 Bronze.

3. Bronze remains close to source data.

4. Bronze contains:

   tenant_id
   pipeline_id
   run_id
   source_system
   ingestion_timestamp


5. PySpark reads Bronze from S3.

6. Silver performs data validation and cleansing.

7. Invalid data is quarantined in S3.

8. Silver quality metrics are stored in S3.

9. Gold reads only trusted Silver data.

10. Gold joins:

    products
    sales
    inventory
    promotions
    suppliers


11. Gold calculates:

    gross_amount
    discount_amount
    final_price
    net_price


12. Gold contains:

    promotion_applied
    inventory_available


13. Gold is suitable for pricing and analytics.

14. All layers are stored in AWS S3.

15. All datasets use Parquet.

16. Tenant isolation is maintained.

17. tenant_id, pipeline_id and run_id remain available
    across Bronze → Silver → Gold.

18. Pipeline execution can be traced end-to-end.

19. The pipeline supports full and incremental ingestion.

20. The pipeline generates ingestion, quality and pipeline
    execution logs.

21. The pipeline can be rerun without uncontrolled duplication.

22. AWS credentials are never hardcoded.

23. The implementation uses PySpark for actual data
    transformations rather than replacing Spark with Pandas.


============================================================
55. FUTURE-READY DESIGN
============================================================

Design the implementation so that the MVP can later evolve to:

FastAPI
   ↓
AWS ingestion service
   ↓
Amazon S3
   ↓
AWS Glue Data Catalog
   ↓
Apache Spark / EMR / AWS Glue
   ↓
Bronze
   ↓
Silver
   ↓
Gold
   ↓
Amazon Athena / Redshift / BI / ML


For this MVP, DO NOT require:

AWS Glue
EMR
Redshift
Athena
Airflow
Databricks


Keep the implementation focused on:

FastAPI
+
PySpark
+
S3
+
Parquet


However, structure the code so these AWS services can be added
later without redesigning the entire pipeline.