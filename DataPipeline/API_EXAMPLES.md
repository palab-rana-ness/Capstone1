# API Usage Examples

This file contains practical examples of using the Retail Mock Data Platform API.

## Quick Start

### 1. Start the Server

```bash
uvicorn app.main:app --reload
```

### 2. Check Health

```bash
curl http://localhost:8000/health
```

## Products Endpoint Examples

### List All Products for a Tenant

```bash
curl -X GET "http://localhost:8000/api/v1/products" \
  -H "X-Tenant-ID: tenant_001"
```

**Response:**
```json
{
  "data": [
    {
      "product_id": "prod_001_00001",
      "tenant_id": "tenant_001",
      "sku": "SKU-000001",
      "product_name": "valuable quick",
      "description": "Affect authority yourself maybe friend education...",
      "category_id": "cat_electronics",
      "category_name": "Electronics",
      "brand": "Johnson LLC",
      "supplier_id": "sup_001_001",
      "unit_price": 2043.50,
      "cost_price": 1243.16,
      "currency": "INR",
      "tax_rate": 18,
      "unit_of_measure": "piece",
      "status": "ACTIVE",
      "created_at": "2025-11-24T14:23:45.123456",
      "updated_at": "2026-09-25T12:00:00Z"
    }
  ],
  "metadata": {
    "tenant_id": "tenant_001",
    "source_system": "product_database",
    "entity": "product",
    "schema_version": "1.0",
    "request_timestamp": "2026-09-25T14:23:45.123456Z",
    "record_count": 100
  },
  "pagination": {
    "record_count": 100,
    "limit": 100,
    "offset": 0,
    "has_more": false
  }
}
```

### Get a Specific Product

```bash
curl -X GET "http://localhost:8000/api/v1/products/prod_001_00001" \
  -H "X-Tenant-ID: tenant_001"
```

**Response:**
```json
{
  "data": {
    "product_id": "prod_001_00001",
    "tenant_id": "tenant_001",
    "sku": "SKU-000001",
    "product_name": "valuable quick",
    "category_id": "cat_electronics",
    "category_name": "Electronics",
    "brand": "Johnson LLC",
    "supplier_id": "sup_001_001",
    "unit_price": 2043.50,
    "cost_price": 1243.16,
    "currency": "INR",
    "tax_rate": 18,
    "unit_of_measure": "piece",
    "status": "ACTIVE",
    "created_at": "2025-11-24T14:23:45.123456",
    "updated_at": "2026-09-25T12:00:00Z"
  },
  "metadata": {
    "tenant_id": "tenant_001",
    "source_system": "product_database",
    "entity": "product",
    "schema_version": "1.0",
    "request_timestamp": "2026-09-25T14:23:45.123456Z",
    "record_count": 1
  }
}
```

### Filter Products by Category

```bash
curl -X GET "http://localhost:8000/api/v1/products?category_id=cat_electronics" \
  -H "X-Tenant-ID: tenant_001"
```

### Filter Products by Status

```bash
curl -X GET "http://localhost:8000/api/v1/products?status=ACTIVE" \
  -H "X-Tenant-ID: tenant_001"
```

### Pagination Example

```bash
# First page
curl -X GET "http://localhost:8000/api/v1/products?limit=20&offset=0" \
  -H "X-Tenant-ID: tenant_001"

# Second page
curl -X GET "http://localhost:8000/api/v1/products?limit=20&offset=20" \
  -H "X-Tenant-ID: tenant_001"

# Large page
curl -X GET "http://localhost:8000/api/v1/products?limit=500&offset=0" \
  -H "X-Tenant-ID: tenant_001"
```

### Incremental Extraction (CDC)

```bash
# Get products updated since yesterday
curl -X GET "http://localhost:8000/api/v1/products?updated_since=2026-09-24T00:00:00Z" \
  -H "X-Tenant-ID: tenant_001"
```

## Suppliers Endpoint Examples

### List All Suppliers

```bash
curl -X GET "http://localhost:8000/api/v1/suppliers" \
  -H "X-Tenant-ID: tenant_001"
```

### Get Active Suppliers Only

```bash
curl -X GET "http://localhost:8000/api/v1/suppliers?status=ACTIVE" \
  -H "X-Tenant-ID: tenant_001"
```

### Get Specific Supplier

```bash
curl -X GET "http://localhost:8000/api/v1/suppliers/sup_001_001" \
  -H "X-Tenant-ID: tenant_001"
```

## Inventory Endpoint Examples

### List All Inventory

```bash
curl -X GET "http://localhost:8000/api/v1/inventory" \
  -H "X-Tenant-ID: tenant_001"
```

### Get Inventory for a Product

```bash
curl -X GET "http://localhost:8000/api/v1/inventory/product/prod_001_00001" \
  -H "X-Tenant-ID: tenant_001"
```

### Get Inventory at a Location

```bash
curl -X GET "http://localhost:8000/api/v1/inventory/location/WH_001_001" \
  -H "X-Tenant-ID: tenant_001"
```

### Get Low Stock Items

```bash
curl -X GET "http://localhost:8000/api/v1/inventory?low_stock=true" \
  -H "X-Tenant-ID: tenant_001"
```

**Response (Low Stock Example):**
```json
{
  "data": [
    {
      "inventory_id": "inv_001_000001",
      "tenant_id": "tenant_001",
      "product_id": "prod_001_00001",
      "location_id": "WH_001_001",
      "location_type": "WAREHOUSE",
      "quantity_on_hand": 45,
      "quantity_reserved": 10,
      "quantity_available": 35,
      "reorder_level": 50,
      "reorder_quantity": 200,
      "last_restocked_at": "2026-09-10T10:30:00Z",
      "updated_at": "2026-09-25T12:00:00Z"
    }
  ],
  "metadata": {
    "tenant_id": "tenant_001",
    "source_system": "inventory_api",
    "entity": "inventory",
    "schema_version": "1.0",
    "request_timestamp": "2026-09-25T14:23:45.123456Z",
    "record_count": 1
  }
}
```

## Promotions Endpoint Examples

### List All Promotions

```bash
curl -X GET "http://localhost:8000/api/v1/promotions" \
  -H "X-Tenant-ID: tenant_001"
```

### Get Active Promotions

```bash
curl -X GET "http://localhost:8000/api/v1/promotions/active" \
  -H "X-Tenant-ID: tenant_001"
```

**Response:**
```json
{
  "data": [
    {
      "promotion_id": "promo_001_0001",
      "tenant_id": "tenant_001",
      "promotion_code": "PROMO0001",
      "promotion_name": "Summer Sale 2026",
      "description": "20% off all electronics",
      "promotion_type": "CATEGORY_DISCOUNT",
      "discount_type": "PERCENTAGE",
      "discount_value": 20.0,
      "start_date": "2026-09-01T00:00:00Z",
      "end_date": "2026-09-30T23:59:59Z",
      "minimum_quantity": 1,
      "maximum_discount": 5000.0,
      "status": "ACTIVE",
      "created_at": "2026-08-20T10:30:00Z",
      "updated_at": "2026-09-25T12:00:00Z"
    }
  ],
  "metadata": {
    "tenant_id": "tenant_001",
    "source_system": "promotion_api",
    "entity": "promotion",
    "schema_version": "1.0",
    "request_timestamp": "2026-09-25T14:23:45.123456Z",
    "record_count": 15
  }
}
```

### Get Promotions for a Product

```bash
curl -X GET "http://localhost:8000/api/v1/products/prod_001_00001/promotions" \
  -H "X-Tenant-ID: tenant_001"
```

## Sales Orders Endpoint Examples

### List All Sales Orders

```bash
curl -X GET "http://localhost:8000/api/v1/sales/orders" \
  -H "X-Tenant-ID: tenant_001"
```

### Get Orders by Date Range

```bash
curl -X GET "http://localhost:8000/api/v1/sales/orders?date_from=2026-09-01T00:00:00Z&date_to=2026-09-25T23:59:59Z" \
  -H "X-Tenant-ID: tenant_001"
```

### Get Orders by Status

```bash
curl -X GET "http://localhost:8000/api/v1/sales/orders?status=DELIVERED" \
  -H "X-Tenant-ID: tenant_001"
```

### Get Orders by Store

```bash
curl -X GET "http://localhost:8000/api/v1/sales/orders?store_id=store_001_01" \
  -H "X-Tenant-ID: tenant_001"
```

### Get a Specific Order

```bash
curl -X GET "http://localhost:8000/api/v1/sales/orders/ord_001_000001" \
  -H "X-Tenant-ID: tenant_001"
```

**Response:**
```json
{
  "data": {
    "order_id": "ord_001_000001",
    "tenant_id": "tenant_001",
    "customer_id": "cust_001_00001",
    "store_id": "store_001_01",
    "order_date": "2026-09-20T10:30:00Z",
    "order_status": "DELIVERED",
    "payment_method": "CREDIT_CARD",
    "currency": "INR",
    "total_amount": 15000.00,
    "discount_amount": 1500.00,
    "tax_amount": 2520.00,
    "net_amount": 16020.00,
    "created_at": "2026-09-20T10:30:00Z",
    "updated_at": "2026-09-25T12:00:00Z"
  },
  "metadata": {
    "tenant_id": "tenant_001",
    "source_system": "sales_database",
    "entity": "sales_order",
    "schema_version": "1.0",
    "request_timestamp": "2026-09-25T14:23:45.123456Z",
    "record_count": 1
  }
}
```

### Get Order Items

```bash
curl -X GET "http://localhost:8000/api/v1/sales/orders/ord_001_000001/items" \
  -H "X-Tenant-ID: tenant_001"
```

**Response:**
```json
{
  "data": [
    {
      "order_item_id": "oi_001_00000001",
      "order_id": "ord_001_000001",
      "tenant_id": "tenant_001",
      "product_id": "prod_001_00001",
      "quantity": 2,
      "unit_price": 7500.00,
      "discount_amount": 1500.00,
      "tax_amount": 2160.00,
      "line_total": 8160.00
    },
    {
      "order_item_id": "oi_001_00000002",
      "order_id": "ord_001_000001",
      "tenant_id": "tenant_001",
      "product_id": "prod_001_00002",
      "quantity": 1,
      "unit_price": 5000.00,
      "discount_amount": 0.00,
      "tax_amount": 900.00,
      "line_total": 5900.00
    }
  ],
  "metadata": {
    "tenant_id": "tenant_001",
    "source_system": "sales_database",
    "entity": "sales_order_item",
    "schema_version": "1.0",
    "request_timestamp": "2026-09-25T14:23:45.123456Z",
    "record_count": 2
  }
}
```

### Get Sales Transactions (Order + Items)

```bash
curl -X GET "http://localhost:8000/api/v1/sales/transactions" \
  -H "X-Tenant-ID: tenant_001"
```

## Customers Endpoint Examples

### List All Customers

```bash
curl -X GET "http://localhost:8000/api/v1/customers" \
  -H "X-Tenant-ID: tenant_001"
```

### Filter Customers by Segment

```bash
curl -X GET "http://localhost:8000/api/v1/customers?customer_segment=PREMIUM" \
  -H "X-Tenant-ID: tenant_001"
```

### Filter Customers by City

```bash
curl -X GET "http://localhost:8000/api/v1/customers?city=Mumbai" \
  -H "X-Tenant-ID: tenant_001"
```

## Stores Endpoint Examples

### List All Stores

```bash
curl -X GET "http://localhost:8000/api/v1/stores" \
  -H "X-Tenant-ID: tenant_001"
```

### Filter Stores by Type

```bash
curl -X GET "http://localhost:8000/api/v1/stores?store_type=FLAGSHIP" \
  -H "X-Tenant-ID: tenant_001"
```

### Get Active Stores

```bash
curl -X GET "http://localhost:8000/api/v1/stores?status=ACTIVE" \
  -H "X-Tenant-ID: tenant_001"
```

## Categories Endpoint Examples

### List All Categories

```bash
curl -X GET "http://localhost:8000/api/v1/categories" \
  -H "X-Tenant-ID: tenant_001"
```

## Tenant Management Examples

### List All Tenants

```bash
curl -X GET "http://localhost:8000/api/v1/tenants"
```

**Response:**
```json
{
  "data": [
    {
      "tenant_id": "tenant_001",
      "tenant_name": "RetailMart India",
      "created_at": "2026-09-25T12:00:00Z",
      "updated_at": "2026-09-25T12:00:00Z"
    },
    {
      "tenant_id": "tenant_002",
      "tenant_name": "SuperStore India",
      "created_at": "2026-09-25T12:00:00Z",
      "updated_at": "2026-09-25T12:00:00Z"
    },
    {
      "tenant_id": "tenant_003",
      "tenant_name": "QuickBuy India",
      "created_at": "2026-09-25T12:00:00Z",
      "updated_at": "2026-09-25T12:00:00Z"
    }
  ],
  "metadata": {
    "source_system": "tenant_management",
    "entity": "tenant",
    "schema_version": "1.0",
    "request_timestamp": "2026-09-25T14:23:45.123456Z",
    "record_count": 3
  }
}
```

## Python Examples

### Using the requests library

```python
import requests
import json

# Configuration
TENANT_ID = "tenant_001"
BASE_URL = "http://localhost:8000/api/v1"
headers = {"X-Tenant-ID": TENANT_ID}

# Get all products
response = requests.get(f"{BASE_URL}/products", headers=headers)
products = response.json()
print(f"Total products: {products['pagination']['record_count']}")

# Get specific product
response = requests.get(f"{BASE_URL}/products/prod_001_00001", headers=headers)
product = response.json()["data"]
print(f"Product: {product['product_name']} - ${product['unit_price']}")

# Get active promotions
response = requests.get(f"{BASE_URL}/promotions/active", headers=headers)
promotions = response.json()["data"]
print(f"Active promotions: {len(promotions)}")

# Get low stock inventory
response = requests.get(f"{BASE_URL}/inventory?low_stock=true", headers=headers)
low_stock = response.json()["data"]
print(f"Low stock items: {len(low_stock)}")

# Get sales orders with pagination
page_size = 50
for page in range(0, 200, page_size):
    response = requests.get(
        f"{BASE_URL}/sales/orders",
        headers=headers,
        params={"limit": page_size, "offset": page}
    )
    orders = response.json()["data"]
    if not orders:
        break
    print(f"Page {page//page_size + 1}: {len(orders)} orders")
```

## Error Response Examples

### Missing Tenant Header

```bash
curl -X GET "http://localhost:8000/api/v1/products"
```

**Response (400):**
```json
{
  "error": {
    "code": "MISSING_TENANT_ID",
    "message": "X-Tenant-ID header is required"
  }
}
```

### Invalid Tenant ID

```bash
curl -X GET "http://localhost:8000/api/v1/products" \
  -H "X-Tenant-ID: invalid_tenant"
```

**Response (400):**
```json
{
  "error": {
    "code": "INVALID_TENANT_ID",
    "message": "Invalid tenant ID: invalid_tenant"
  }
}
```

### Resource Not Found

```bash
curl -X GET "http://localhost:8000/api/v1/products/nonexistent" \
  -H "X-Tenant-ID: tenant_001"
```

**Response (404):**
```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "Product nonexistent was not found for tenant tenant_001"
  }
}
```

### Tenant Isolation (Cross-Tenant Access Denied)

```bash
# First, get a supplier from tenant_002
# Then try to access it as tenant_001

curl -X GET "http://localhost:8000/api/v1/suppliers/sup_002_001" \
  -H "X-Tenant-ID: tenant_001"
```

**Response (404):**
```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "Supplier sup_002_001 was not found for tenant tenant_001"
  }
}
```

## Swagger UI

Visit http://localhost:8000/docs to interact with all endpoints using Swagger UI.

## Testing

Run the full test suite:

```bash
pytest tests/test_api.py -v
```

Run specific test:

```bash
pytest tests/test_api.py::TestProducts::test_list_products -v
```
