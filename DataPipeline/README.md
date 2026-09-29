# Retail Mock Data Platform - FastAPI Multi-Tenant Service

A production-like mock FastAPI server that simulates a multi-tenant retail data platform. This service is designed to mimic enterprise retail systems and expose their data through APIs for downstream Data Lake / Data Engineering pipelines.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Installation](#installation)
- [Running the Server](#running-the-server)
- [API Endpoints](#api-endpoints)
- [Multi-Tenancy](#multi-tenancy)
- [Authentication](#authentication)
- [Data Model](#data-model)
- [Sample API Requests](#sample-api-requests)
- [Data Relationships](#data-relationships)
- [Data Lake Ingestion](#data-lake-ingestion)
- [Incremental Extraction (CDC)](#incremental-extraction-cdc)
- [Pagination](#pagination)
- [Error Handling](#error-handling)
- [Testing](#testing)
- [PySpark Integration Example](#pyspark-integration-example)

## Overview

The Retail Mock Data Platform simulates an interconnected retail ecosystem consisting of:

- **Supplier API**: Supplier information and ratings
- **Product Database**: Product catalog with pricing and inventory references
- **Sales Database**: Sales transactions, orders, and customers
- **Inventory System**: Stock levels across warehouses and stores
- **Promotion System**: Discounts, coupons, and promotional campaigns

All data is stored in-memory using Python data structures. The API is designed to be consumed by data pipelines that need to ingest, transform, and aggregate retail data into a Data Lake.

## Architecture

```
Retail Data Sources (Simulated)
    ↓
FastAPI Mock APIs (In-Memory)
    ↓
Data Ingestion Layer
    ↓
Apache Spark / Python
    ↓
Bronze Layer (Raw Data)
    ↓
Silver Layer (Cleaned & Validated)
    ↓
Gold Layer (Business Ready)
    ↓
Analytics / ML / BI Tools
```

### Project Structure

```
retail-mock-api/
│
├── app/
│   ├── main.py                    # FastAPI application
│   ├── __init__.py
│   │
│   ├── models/
│   │   ├── entities.py            # Dataclass entities
│   │   └── __init__.py
│   │
│   ├── schemas/
│   │   ├── schemas.py             # Pydantic request/response schemas
│   │   └── __init__.py
│   │
│   ├── routers/
│   │   ├── suppliers.py
│   │   ├── products.py
│   │   ├── inventory.py
│   │   ├── promotions.py
│   │   ├── sales.py
│   │   ├── customers.py
│   │   ├── stores.py
│   │   └── __init__.py
│   │
│   ├── data/
│   │   ├── store.py               # In-memory data store
│   │   ├── seed.py                # Seed data generator
│   │   └── __init__.py
│   │
│   ├── middleware/
│   │   ├── tenant.py              # Tenant validation middleware
│   │   └── __init__.py
│   │
│   └── utils/
│       ├── pagination.py           # Pagination utilities
│       └── __init__.py
│
├── tests/
│   ├── test_api.py                # Comprehensive test suite
│   └── __init__.py
│
├── requirements.txt
├── README.md
└── Dockerfile
```

## Installation

### Prerequisites

- Python 3.11+
- pip (Python package manager)

### Setup

1. Clone or download the project:

```bash
cd retail-mock-api
```

2. Create a virtual environment (recommended):

```bash
python -m venv venv
# On Windows
venv\Scripts\activate
# On macOS/Linux
source venv/bin/activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

## Running the Server

Start the FastAPI development server:

```bash
uvicorn app.main:app --reload
```

The server will start on `http://localhost:8000`

### Access Points

- **API Documentation (Swagger UI)**: http://localhost:8000/docs
- **Alternative API Docs (ReDoc)**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

## API Endpoints

### Health Check

```
GET /health
```

Returns service status.

### Tenant Management

```
GET /api/v1/tenants                    # List all tenants
```

### Products

```
GET /api/v1/products                   # List products
GET /api/v1/products/{product_id}      # Get product details
GET /api/v1/products/{product_id}/promotions  # Get promotions for product
GET /api/v1/categories                 # List categories
```

Query Parameters:
- `category_id`: Filter by category
- `supplier_id`: Filter by supplier
- `status`: Filter by product status
- `limit`: Pagination limit (1-1000, default: 100)
- `offset`: Pagination offset (default: 0)
- `updated_since`: ISO-8601 timestamp for incremental extraction

### Suppliers

```
GET /api/v1/suppliers                  # List suppliers
GET /api/v1/suppliers/{supplier_id}    # Get supplier details
```

Query Parameters:
- `status`: Filter by supplier status (ACTIVE, INACTIVE, SUSPENDED)
- `limit`, `offset`: Pagination
- `updated_since`: Incremental extraction

### Inventory

```
GET /api/v1/inventory                  # List inventory
GET /api/v1/inventory/product/{product_id}        # Inventory for product
GET /api/v1/inventory/location/{location_id}      # Inventory at location
```

Query Parameters:
- `product_id`: Filter by product
- `location_id`: Filter by location
- `low_stock`: Return only low-stock items (true/false)
- `limit`, `offset`: Pagination
- `updated_since`: Incremental extraction

### Promotions

```
GET /api/v1/promotions                 # List promotions
GET /api/v1/promotions/active          # List active promotions
GET /api/v1/promotions/{promotion_id}  # Get promotion details
```

Query Parameters:
- `status`: Filter by status
- `promotion_type`: Filter by type
- `limit`, `offset`: Pagination

### Sales

```
GET /api/v1/sales/orders               # List sales orders
GET /api/v1/sales/orders/{order_id}    # Get order details
GET /api/v1/sales/orders/{order_id}/items  # Get order items
GET /api/v1/sales/transactions         # Get sales transactions (order + items)
```

Query Parameters:
- `store_id`: Filter by store
- `product_id`: Filter by product in order items
- `status`: Filter by order status
- `date_from`, `date_to`: Filter by date range
- `limit`, `offset`: Pagination
- `updated_since`: Incremental extraction

### Customers

```
GET /api/v1/customers                  # List customers
GET /api/v1/customers/{customer_id}    # Get customer details
```

Query Parameters:
- `customer_segment`: Filter by segment (PREMIUM, REGULAR, BUDGET, VIP)
- `city`: Filter by city
- `limit`, `offset`: Pagination

### Stores

```
GET /api/v1/stores                     # List stores
GET /api/v1/stores/{store_id}          # Get store details
```

Query Parameters:
- `store_type`: Filter by type (FLAGSHIP, STANDARD, POPUP, WAREHOUSE)
- `status`: Filter by status
- `city`: Filter by city
- `limit`, `offset`: Pagination

## Multi-Tenancy

The platform supports multiple isolated tenants. Each request must include the `X-Tenant-ID` header.

### Available Tenants

- `tenant_001`: RetailMart India
- `tenant_002`: SuperStore India
- `tenant_003`: QuickBuy India

### Tenant Isolation Rules

1. **Required Header**: Every API request (except `/health` and `/api/v1/tenants`) must include `X-Tenant-ID` header
2. **Validation**: Invalid or missing tenant IDs return HTTP 400
3. **Data Filtering**: The API automatically filters data to the tenant
4. **No Cross-Tenant Access**: Attempting to access another tenant's data returns 404

### Example with curl

```bash
curl -X GET "http://localhost:8000/api/v1/products" \
  -H "X-Tenant-ID: tenant_001"
```

## Authentication

The current version uses header-based tenant identification. A future version might implement:
- OAuth2 with tenant scoping
- JWT tokens with tenant claims
- API keys per tenant

## Data Model

### Common Fields

All major entities include:

```json
{
  "id": "unique_identifier",
  "tenant_id": "tenant_001",
  "created_at": "2026-09-20T10:30:00Z",
  "updated_at": "2026-09-24T14:20:00Z"
}
```

### Product

```json
{
  "product_id": "prod_001_00001",
  "tenant_id": "tenant_001",
  "sku": "SKU-LAP-001",
  "product_name": "Laptop Pro 14",
  "description": "High-performance laptop",
  "category_id": "cat_electronics",
  "category_name": "Electronics",
  "brand": "TechBrand",
  "supplier_id": "sup_001_001",
  "unit_price": 75000.00,
  "cost_price": 60000.00,
  "currency": "INR",
  "tax_rate": 18,
  "unit_of_measure": "piece",
  "status": "ACTIVE",
  "created_at": "2026-09-20T10:30:00Z",
  "updated_at": "2026-09-24T14:20:00Z"
}
```

### Supplier

```json
{
  "supplier_id": "sup_001_001",
  "tenant_id": "tenant_001",
  "supplier_code": "SUP-0001",
  "supplier_name": "Global Tech Supplies",
  "contact_email": "contact@suppliertech.com",
  "phone": "+91-9876543210",
  "country": "India",
  "city": "Mumbai",
  "rating": 4.5,
  "payment_terms": "30 days",
  "status": "ACTIVE",
  "created_at": "2026-09-20T10:30:00Z",
  "updated_at": "2026-09-24T14:20:00Z"
}
```

### SalesOrder

```json
{
  "order_id": "ord_001_000001",
  "tenant_id": "tenant_001",
  "customer_id": "cust_001_00001",
  "store_id": "store_001_01",
  "order_date": "2026-09-24T10:30:00Z",
  "order_status": "DELIVERED",
  "payment_method": "CREDIT_CARD",
  "currency": "INR",
  "total_amount": 150000.00,
  "discount_amount": 10000.00,
  "tax_amount": 25200.00,
  "net_amount": 165200.00,
  "created_at": "2026-09-24T10:30:00Z",
  "updated_at": "2026-09-24T14:20:00Z"
}
```

### Inventory

```json
{
  "inventory_id": "inv_001_000001",
  "tenant_id": "tenant_001",
  "product_id": "prod_001_00001",
  "location_id": "WH_001_001",
  "location_type": "WAREHOUSE",
  "quantity_on_hand": 500,
  "quantity_reserved": 100,
  "quantity_available": 400,
  "reorder_level": 50,
  "reorder_quantity": 200,
  "last_restocked_at": "2026-09-20T10:30:00Z",
  "updated_at": "2026-09-24T14:20:00Z"
}
```

### Promotion

```json
{
  "promotion_id": "promo_001_0001",
  "tenant_id": "tenant_001",
  "promotion_code": "PROMO0001",
  "promotion_name": "Summer Sale",
  "description": "20% off electronics",
  "promotion_type": "CATEGORY_DISCOUNT",
  "discount_type": "PERCENTAGE",
  "discount_value": 20.0,
  "start_date": "2026-09-01T00:00:00Z",
  "end_date": "2026-09-30T23:59:59Z",
  "minimum_quantity": 1,
  "maximum_discount": 5000.0,
  "status": "ACTIVE",
  "created_at": "2026-09-20T10:30:00Z",
  "updated_at": "2026-09-24T14:20:00Z"
}
```

## Sample API Requests

### Using curl

#### List Products for a Tenant

```bash
curl -X GET "http://localhost:8000/api/v1/products?limit=10" \
  -H "X-Tenant-ID: tenant_001"
```

#### Get a Specific Product

```bash
curl -X GET "http://localhost:8000/api/v1/products/prod_001_00001" \
  -H "X-Tenant-ID: tenant_001"
```

#### List Suppliers with Status Filter

```bash
curl -X GET "http://localhost:8000/api/v1/suppliers?status=ACTIVE" \
  -H "X-Tenant-ID: tenant_001"
```

#### Get Sales Orders in Date Range

```bash
curl -X GET "http://localhost:8000/api/v1/sales/orders?date_from=2026-09-01T00:00:00Z&date_to=2026-09-25T23:59:59Z" \
  -H "X-Tenant-ID: tenant_001"
```

#### Get Inventory with Low Stock Filter

```bash
curl -X GET "http://localhost:8000/api/v1/inventory?low_stock=true" \
  -H "X-Tenant-ID: tenant_001"
```

#### Get Active Promotions

```bash
curl -X GET "http://localhost:8000/api/v1/promotions/active" \
  -H "X-Tenant-ID: tenant_001"
```

### Using Python (requests)

```python
import requests

tenant_id = "tenant_001"
headers = {"X-Tenant-ID": tenant_id}
base_url = "http://localhost:8000/api/v1"

# Get products
response = requests.get(f"{base_url}/products", headers=headers)
products = response.json()
print(f"Retrieved {len(products['data'])} products")

# Get suppliers
response = requests.get(f"{base_url}/suppliers?status=ACTIVE", headers=headers)
suppliers = response.json()
print(f"Retrieved {len(suppliers['data'])} active suppliers")

# Get sales orders
response = requests.get(f"{base_url}/sales/orders", headers=headers)
orders = response.json()
print(f"Retrieved {len(orders['data'])} orders")
```

## Sample API Responses

### Response Envelope

All API responses follow a consistent envelope format:

```json
{
  "data": [...],
  "metadata": {
    "tenant_id": "tenant_001",
    "source_system": "product_database",
    "entity": "product",
    "schema_version": "1.0",
    "request_timestamp": "2026-09-24T14:20:00Z",
    "record_count": 10
  },
  "pagination": {
    "record_count": 10,
    "limit": 100,
    "offset": 0,
    "has_more": false
  }
}
```

### Error Response

```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "Product prod_001_00001 was not found for tenant tenant_001"
  }
}
```

## Data Relationships

### ER Diagram

```
Supplier
   |
   | (1:N)
   ↓
Product ←─────────────────┐
   |                      |
   ├──→ Inventory         |
   |                      |
   ├──→ PromotionProduct  |
   |    |                 |
   |    └──→ Promotion    |
   |                      |
   └──→ SalesOrderItem────┘
        |
        └─→ SalesOrder
             |
             ├─→ Customer
             └─→ Store
```

### Key Relationships

| From | To | Type | Description |
|------|-------|------|-------------|
| Supplier | Product | 1:N | A supplier can supply multiple products |
| Product | Inventory | 1:N | Product can have multiple inventory records across locations |
| Product | SalesOrderItem | 1:N | Product appears in multiple order items |
| SalesOrder | SalesOrderItem | 1:N | Order contains multiple items |
| Product | Promotion | N:N | Products can have multiple promotions via PromotionProduct |
| Customer | SalesOrder | 1:N | Customer can have multiple orders |
| Store | SalesOrder | 1:N | Store can process multiple orders |

## Data Lake Ingestion

### API Design for Data Lake Consumption

The API is designed for easy ingestion into data lakes:

1. **Stable Primary Keys**: All entities have stable `id` fields
2. **Tenant Isolation**: `tenant_id` for multi-tenant scenarios
3. **Timestamps**: `created_at` and `updated_at` for SCD tracking
4. **Source System Metadata**: `source_system` indicates origin
5. **Relationship IDs**: Foreign keys are ID references, not embedded objects

### Data Lake Architecture

```
FastAPI ← requests → Spark/Python
          ↓ JSON
          DataFrame
          ↓
          Bronze (Raw)
          ↓
          Silver (Cleaned)
          ↓
          Gold (Aggregated)
          ↓
          Analytics/BI
```

### Example: Ingestion Flow

1. **Extract**: Call API for products
2. **Transform**: Convert JSON to DataFrame
3. **Load**: Write to Bronze layer in Parquet/Delta
4. **Validate**: Check referential integrity
5. **Aggregate**: Join with other datasets in Silver layer

## Incremental Extraction (CDC)

The API supports Change Data Capture (CDC) patterns using the `updated_since` parameter:

### CDC Query Pattern

```bash
# First run: Get all data
GET /api/v1/products

# Subsequent runs: Get only changed data
GET /api/v1/products?updated_since=2026-09-24T00:00:00Z
```

### All Entities Support `updated_since`:

- Products
- Suppliers
- Sales Orders
- Inventory
- Promotions
- Customers
- Stores

### Example CDC Workflow

```python
import requests
from datetime import datetime, timedelta

tenant_id = "tenant_001"
headers = {"X-Tenant-ID": tenant_id}
base_url = "http://localhost:8000/api/v1"

# Load watermark from previous run
last_extracted = datetime.utcnow() - timedelta(days=1)

# Extract incremental data
response = requests.get(
    f"{base_url}/products",
    headers=headers,
    params={"updated_since": last_extracted.isoformat() + "Z"}
)

products = response.json()["data"]
print(f"Extracted {len(products)} changed products")

# Update watermark for next run
with open("watermark.txt", "w") as f:
    f.write(datetime.utcnow().isoformat() + "Z")
```

## Pagination

All list endpoints support pagination:

### Pagination Parameters

- `limit`: Number of records per page (1-1000, default: 100)
- `offset`: Starting position (default: 0)

### Pagination Response

```json
{
  "data": [...],
  "pagination": {
    "record_count": 100,
    "limit": 100,
    "offset": 0,
    "has_more": true
  }
}
```

### Example

```bash
# Get first 50 products
GET /api/v1/products?limit=50&offset=0

# Get next 50 products
GET /api/v1/products?limit=50&offset=50
```

## Error Handling

### HTTP Status Codes

| Code | Meaning | Example |
|------|---------|---------|
| 200 | Success | Product retrieved |
| 400 | Bad Request | Missing X-Tenant-ID header |
| 404 | Not Found | Product doesn't exist |
| 422 | Validation Error | Invalid query parameter |
| 500 | Server Error | Unexpected error |

### Error Response Format

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message"
  }
}
```

### Common Error Codes

- `MISSING_TENANT_ID`: X-Tenant-ID header not provided
- `INVALID_TENANT_ID`: X-Tenant-ID doesn't exist
- `RESOURCE_NOT_FOUND`: Resource not found for tenant
- `VALIDATION_ERROR`: Invalid request parameters

## Testing

### Run All Tests

```bash
pytest tests/
```

### Run Specific Test Class

```bash
pytest tests/test_api.py::TestProducts
```

### Run with Verbose Output

```bash
pytest -v tests/
```

### Run with Coverage

```bash
pytest --cov=app tests/
```

### Test Categories

The test suite covers:

1. **Health Checks**: Service status
2. **Tenant Isolation**: Cross-tenant data isolation
3. **Products**: CRUD and filtering
4. **Suppliers**: Supplier endpoints
5. **Inventory**: Stock levels and low-stock filtering
6. **Promotions**: Active promotions
7. **Sales**: Orders and transactions
8. **Customers & Stores**: Supporting entities
9. **Relationships**: Data integrity and relationships
10. **Pagination**: Offset/limit functionality
11. **CDC**: Updated_since filtering

### Test Execution

```bash
# Run all tests
pytest tests/test_api.py -v

# Run specific test
pytest tests/test_api.py::TestTenantIsolation -v

# Run with output
pytest tests/test_api.py -s
```

## PySpark Integration Example

### Basic Ingestion

```python
from pyspark.sql import SparkSession
import requests
from datetime import datetime, timedelta

# Initialize Spark
spark = SparkSession.builder.appName("RetailDataLake").getOrCreate()

# Configuration
TENANT_ID = "tenant_001"
API_BASE = "http://localhost:8000/api/v1"
HEADERS = {"X-Tenant-ID": TENANT_ID}

# 1. Extract products from API
def extract_products(endpoint, updated_since=None):
    """Extract products from API."""
    params = {"limit": 1000, "offset": 0}
    if updated_since:
        params["updated_since"] = updated_since
    
    all_data = []
    while True:
        response = requests.get(f"{API_BASE}{endpoint}", 
                              headers=HEADERS, 
                              params=params)
        data = response.json()
        all_data.extend(data["data"])
        
        if not data["pagination"]["has_more"]:
            break
        
        params["offset"] += params["limit"]
    
    return all_data

# 2. Load into DataFrame (Bronze)
products_data = extract_products("/products")
products_df = spark.createDataFrame(products_data)
products_df.show()

# 3. Save to Bronze Layer
products_df.write.mode("overwrite").parquet("s3://data-lake/bronze/products")

# 4. Transform (Silver)
silver_df = products_df.select(
    "product_id",
    "tenant_id",
    "sku",
    "product_name",
    "category_name",
    "unit_price",
    "cost_price",
    "status",
    "created_at",
    "updated_at"
).filter("status = 'ACTIVE'")

silver_df.write.mode("overwrite").parquet("s3://data-lake/silver/products")

# 5. Aggregate (Gold)
gold_df = silver_df.groupBy("category_name").agg({
    "unit_price": "avg",
    "cost_price": "sum",
    "product_id": "count"
})

gold_df.write.mode("overwrite").parquet("s3://data-lake/gold/products_summary")

print("Data Lake ingestion complete!")
```

### Incremental Ingestion

```python
from datetime import datetime, timedelta

# Read last extraction time
try:
    with open("last_extraction.txt", "r") as f:
        last_extraction = f.read().strip()
except FileNotFoundError:
    last_extraction = (datetime.utcnow() - timedelta(days=1)).isoformat() + "Z"

# Extract changed data
changed_products = extract_products("/products", updated_since=last_extraction)

# Append to existing Bronze data
changed_df = spark.createDataFrame(changed_products)
bronze_df = spark.read.parquet("s3://data-lake/bronze/products")
merged_df = bronze_df.unionByName(changed_df, allowMissingColumns=True)

# Upsert to Silver
merged_df.write.mode("overwrite").parquet("s3://data-lake/bronze/products")

# Update watermark
with open("last_extraction.txt", "w") as f:
    f.write(datetime.utcnow().isoformat() + "Z")

print(f"Ingested {len(changed_products)} changed records")
```

### Multi-Entity Ingestion

```python
def ingest_all_entities(tenant_id, last_extraction=None):
    """Ingest all retail entities."""
    
    entities = [
        ("products", "/products"),
        ("suppliers", "/suppliers"),
        ("orders", "/sales/orders"),
        ("inventory", "/inventory"),
        ("promotions", "/promotions"),
    ]
    
    for entity_name, endpoint in entities:
        print(f"Ingesting {entity_name}...")
        
        data = extract_products(endpoint, updated_since=last_extraction)
        df = spark.createDataFrame(data)
        
        df.write.mode("append").parquet(f"s3://data-lake/bronze/{entity_name}")
        print(f"  ✓ Wrote {len(data)} records")

# Run ingestion
ingest_all_entities("tenant_001")
```

## Deployment

### Docker

```dockerfile
# Build image
docker build -t retail-mock-api:latest .

# Run container
docker run -p 8000:8000 retail-mock-api:latest
```

### Production Considerations

1. **Database**: Replace in-memory storage with PostgreSQL
2. **Authentication**: Implement OAuth2 or JWT
3. **Rate Limiting**: Add rate limiting middleware
4. **Caching**: Implement Redis caching
5. **Monitoring**: Add Prometheus metrics
6. **Logging**: Centralized logging (ELK stack)
7. **CI/CD**: GitHub Actions or Jenkins

## Seed Data Summary

The application generates deterministic seed data for realistic testing:

- **3 Tenants**: tenant_001, tenant_002, tenant_003
- **10 Categories** per tenant
- **10 Suppliers** per tenant
- **50 Products** per tenant with valid supplier relationships
- **10 Stores** per tenant
- **100 Customers** per tenant
- **50 Promotions** per tenant with product associations
- **1000 Sales Orders** per tenant
- **2000+ Sales Order Items** per tenant
- **100+ Inventory Records** per product across locations

All data is generated with realistic values:
- Valid foreign key relationships
- Realistic prices and tax rates
- Authentic timestamps
- Proper tenant isolation

## Future Enhancements

1. **Real Database Backend**: PostgreSQL/MySQL integration
2. **Authentication**: OAuth2, JWT tokens
3. **Real-time Updates**: WebSocket support
4. **Caching**: Redis for frequently accessed data
5. **Search**: Full-text search capabilities
6. **Analytics**: Built-in aggregation endpoints
7. **Webhooks**: Event-driven architecture
8. **Versioning**: API versioning strategy
9. **GraphQL**: GraphQL interface
10. **SDKs**: Python, Node.js, Java SDKs

## Troubleshooting

### Port Already in Use

```bash
# Find process on port 8000
lsof -i :8000

# Kill process
kill -9 <PID>

# Or use different port
uvicorn app.main:app --reload --port 8001
```

### Import Errors

```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

### Seed Data Not Loading

```bash
# Check logs for seed data initialization
python -m app.main
```

## Contributing

To extend this mock API:

1. Add new models in `app/models/entities.py`
2. Create Pydantic schemas in `app/schemas/schemas.py`
3. Implement data generation in `app/data/seed.py`
4. Create API endpoints in `app/routers/`
5. Add tests in `tests/`

## License

This project is for demonstration and educational purposes.

## Support

For issues or questions, refer to the inline code comments and the comprehensive test suite.

---

**Happy Data Lake Ingesting! 🚀**
