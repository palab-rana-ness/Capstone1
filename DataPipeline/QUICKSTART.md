# Quick Start Guide

## Installation (5 minutes)

### 1. Navigate to project directory

```bash
cd c:\New_workspace\CapstoneProject
```

### 2. Create virtual environment (recommended)

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

## Running the Server (2 minutes)

### Start FastAPI server

```bash
uvicorn app.main:app --reload
```

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete
Starting Retail Mock Data Service...
Generating seed data...
```

### Access the API

Open in browser:
- **Swagger UI**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **ReDoc**: http://localhost:8000/redoc

## Testing the API (5 minutes)

### Option 1: Using Swagger UI

1. Go to http://localhost:8000/docs
2. Find any endpoint (e.g., `/api/v1/products`)
3. Click "Try it out"
4. Add header: `X-Tenant-ID: tenant_001`
5. Click "Execute"

### Option 2: Using curl

```bash
# List products
curl -X GET "http://localhost:8000/api/v1/products" \
  -H "X-Tenant-ID: tenant_001"

# Get a specific product
curl -X GET "http://localhost:8000/api/v1/products/prod_001_00001" \
  -H "X-Tenant-ID: tenant_001"

# List active promotions
curl -X GET "http://localhost:8000/api/v1/promotions/active" \
  -H "X-Tenant-ID: tenant_001"

# Get low stock inventory
curl -X GET "http://localhost:8000/api/v1/inventory?low_stock=true" \
  -H "X-Tenant-ID: tenant_001"
```

### Option 3: Using Python

```python
import requests

tenant_id = "tenant_001"
headers = {"X-Tenant-ID": tenant_id}
base_url = "http://localhost:8000/api/v1"

# Get products
response = requests.get(f"{base_url}/products", headers=headers)
products = response.json()
print(f"Products: {len(products['data'])}")

# Get suppliers
response = requests.get(f"{base_url}/suppliers", headers=headers)
suppliers = response.json()
print(f"Suppliers: {len(suppliers['data'])}")

# Get sales orders
response = requests.get(f"{base_url}/sales/orders", headers=headers)
orders = response.json()
print(f"Orders: {len(orders['data'])}")
```

## Running Tests (5 minutes)

### Run all tests

```bash
pytest tests/test_api.py -v
```

### Run specific test

```bash
pytest tests/test_api.py::TestProducts::test_list_products -v
```

### Run with coverage

```bash
pytest --cov=app tests/
```

## Available Tenants

```
tenant_001 = RetailMart India
tenant_002 = SuperStore India
tenant_003 = QuickBuy India
```

Use any of these in the `X-Tenant-ID` header.

## Key Endpoints

### Products
- `GET /api/v1/products` - List products
- `GET /api/v1/products/{product_id}` - Get product details
- `GET /api/v1/products/{product_id}/promotions` - Get promotions for product

### Suppliers
- `GET /api/v1/suppliers` - List suppliers
- `GET /api/v1/suppliers/{supplier_id}` - Get supplier details

### Sales
- `GET /api/v1/sales/orders` - List orders
- `GET /api/v1/sales/orders/{order_id}` - Get order details
- `GET /api/v1/sales/orders/{order_id}/items` - Get order items
- `GET /api/v1/sales/transactions` - Get orders with items

### Inventory
- `GET /api/v1/inventory` - List inventory
- `GET /api/v1/inventory?low_stock=true` - Get low stock items
- `GET /api/v1/inventory/product/{product_id}` - Get product inventory

### Promotions
- `GET /api/v1/promotions` - List promotions
- `GET /api/v1/promotions/active` - Get active promotions

### Customers
- `GET /api/v1/customers` - List customers
- `GET /api/v1/customers/{customer_id}` - Get customer details

### Stores
- `GET /api/v1/stores` - List stores
- `GET /api/v1/stores/{store_id}` - Get store details

## Seed Data Generated

- **3 Tenants** with isolated data
- **10 Suppliers** per tenant
- **50 Products** per tenant
- **10 Categories** per tenant
- **10 Stores** per tenant
- **100 Customers** per tenant
- **50 Promotions** per tenant
- **1,000 Sales Orders** per tenant
- **2,000+ Sales Order Items** per tenant
- **100+ Inventory Records** per tenant

## Documentation Files

- **README.md** - Comprehensive project documentation
- **API_EXAMPLES.md** - API usage examples with curl and Python
- **data_lake_integration.py** - PySpark integration examples
- **requirements.txt** - Python dependencies
- **Dockerfile** - Docker deployment configuration

## Troubleshooting

### Port 8000 already in use?

```bash
# Run on different port
uvicorn app.main:app --reload --port 8001
```

### Missing X-Tenant-ID header?

All endpoints except `/health` and `/api/v1/tenants` require the header:
```bash
-H "X-Tenant-ID: tenant_001"
```

### Need to reset data?

Simply restart the server. Seed data is regenerated on startup.

## Next Steps

1. **Explore the API**: Use Swagger UI to explore all endpoints
2. **Read the Examples**: Check API_EXAMPLES.md for detailed examples
3. **Data Lake Integration**: Use data_lake_integration.py for Spark ingestion
4. **Customize**: Extend the API by adding new entities or endpoints
5. **Deploy**: Use the Dockerfile to containerize and deploy

## Support

For issues:
1. Check README.md for detailed documentation
2. Review API_EXAMPLES.md for usage patterns
3. Run tests to verify API functionality
4. Check server logs for error messages

---

**Happy exploring! 🚀**
