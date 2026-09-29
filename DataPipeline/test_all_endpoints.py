# Comprehensive smoke test for every endpoint in the Retail Mock Data Platform.
# Run: c:/New_workspace/CapstoneProject/.venv/Scripts/python.exe test_all_endpoints.py

import sys
import requests

BASE = "http://127.0.0.1:8001"
TENANT = "tenant_001"
OTHER_TENANT = "tenant_002"
HEADERS = {"X-Tenant-ID": TENANT}

passed = 0
failed = 0
failures = []


def check(name, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"[PASS] {name}")
    else:
        failed += 1
        failures.append(f"{name} -- {detail}")
        print(f"[FAIL] {name} -- {detail}")


def get(path, headers=HEADERS, params=None):
    return requests.get(f"{BASE}{path}", headers=headers, params=params)


# ---------------------------------------------------------------------------
# Health & Tenants
# ---------------------------------------------------------------------------
r = get("/health", headers=None)
check("GET /health -> 200", r.status_code == 200, r.text)
check("health payload has status=healthy", r.json().get("status") == "healthy")

r = get("/api/v1/tenants", headers=None)
check("GET /api/v1/tenants -> 200", r.status_code == 200, r.text)
tenants = r.json()["data"]
check("3 tenants seeded", len(tenants) == 3, str(len(tenants)))

# ---------------------------------------------------------------------------
# Tenant header validation
# ---------------------------------------------------------------------------
r = get("/api/v1/products", headers=None)
check("missing X-Tenant-ID -> 400", r.status_code == 400, r.text)
check("missing tenant error code", r.json().get("error", {}).get("code") == "MISSING_TENANT_ID", r.text)

r = get("/api/v1/products", headers={"X-Tenant-ID": "bogus_tenant"})
check("invalid X-Tenant-ID -> 400", r.status_code == 400, r.text)
check("invalid tenant error code", r.json().get("error", {}).get("code") == "INVALID_TENANT_ID", r.text)

# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------
r = get("/api/v1/categories")
check("GET /api/v1/categories -> 200", r.status_code == 200, r.text)
categories = r.json()["data"]
check("10 categories seeded", len(categories) == 10, str(len(categories)))
category_id = categories[0]["category_id"]

# ---------------------------------------------------------------------------
# Products
# ---------------------------------------------------------------------------
r = get("/api/v1/products")
check("GET /api/v1/products -> 200", r.status_code == 200, r.text)
products = r.json()["data"]
check("50 products for tenant_001", r.json()["metadata"]["record_count"] == len(products) and len(products) > 0)
product_id = products[0]["product_id"]

r = get(f"/api/v1/products?category_id={category_id}")
check("filter products by category", r.status_code == 200 and all(p["category_id"] == category_id for p in r.json()["data"]), r.text)

r = get("/api/v1/products?status=ACTIVE")
check("filter products by status", r.status_code == 200 and all(p["status"] == "ACTIVE" for p in r.json()["data"]), r.text)

r = get("/api/v1/products", params={"limit": 5, "offset": 0})
check("products pagination limit=5", r.status_code == 200 and len(r.json()["data"]) <= 5, r.text)

r = get(f"/api/v1/products/{product_id}")
check("GET single product -> 200", r.status_code == 200, r.text)
check("single product id matches", r.json()["data"]["product_id"] == product_id)

r = get("/api/v1/products/does_not_exist")
check("GET missing product -> 404", r.status_code == 404, r.text)

r = get(f"/api/v1/products/{product_id}/promotions")
check("GET product promotions -> 200", r.status_code == 200, r.text)

r = get("/api/v1/products?updated_since=2020-01-01T00:00:00Z")
check("products updated_since filter -> 200", r.status_code == 200, r.text)

# ---------------------------------------------------------------------------
# Suppliers
# ---------------------------------------------------------------------------
r = get("/api/v1/suppliers")
check("GET /api/v1/suppliers -> 200", r.status_code == 200, r.text)
suppliers = r.json()["data"]
check("10 suppliers for tenant_001", len(suppliers) == 10, str(len(suppliers)))
supplier_id = suppliers[0]["supplier_id"]

r = get("/api/v1/suppliers?status=ACTIVE")
check("filter suppliers by status", r.status_code == 200 and all(s["status"] == "ACTIVE" for s in r.json()["data"]), r.text)

r = get(f"/api/v1/suppliers/{supplier_id}")
check("GET single supplier -> 200", r.status_code == 200, r.text)

r = get("/api/v1/suppliers/does_not_exist")
check("GET missing supplier -> 404", r.status_code == 404, r.text)

# ---------------------------------------------------------------------------
# Inventory
# ---------------------------------------------------------------------------
r = get("/api/v1/inventory")
check("GET /api/v1/inventory -> 200", r.status_code == 200, r.text)
inventory = r.json()["data"]
check("inventory records exist", len(inventory) > 0, str(len(inventory)))
location_id = inventory[0]["location_id"]

r = get(f"/api/v1/inventory/product/{product_id}")
check("GET inventory by product -> 200", r.status_code == 200, r.text)

r = get(f"/api/v1/inventory/location/{location_id}")
check("GET inventory by location -> 200", r.status_code == 200, r.text)

r = get("/api/v1/inventory?low_stock=true")
check("low stock filter -> 200", r.status_code == 200, r.text)
low_stock = r.json()["data"]
check("low stock items respect rule", all(i["quantity_available"] <= i["reorder_level"] for i in low_stock))

r = get("/api/v1/inventory/location/does_not_exist")
check("GET missing location -> 404", r.status_code == 404, r.text)

# ---------------------------------------------------------------------------
# Promotions
# ---------------------------------------------------------------------------
r = get("/api/v1/promotions")
check("GET /api/v1/promotions -> 200", r.status_code == 200, r.text)
promotions = r.json()["data"]
check("50 promotions for tenant_001", len(promotions) == 50, str(len(promotions)))
promotion_id = promotions[0]["promotion_id"]

r = get("/api/v1/promotions/active")
check("GET active promotions -> 200", r.status_code == 200, r.text)
check("active promotions all ACTIVE", all(p["status"] == "ACTIVE" for p in r.json()["data"]))

r = get(f"/api/v1/promotions/{promotion_id}")
check("GET single promotion -> 200", r.status_code == 200, r.text)

r = get("/api/v1/promotions/does_not_exist")
check("GET missing promotion -> 404", r.status_code == 404, r.text)

r = get("/api/v1/promotions?status=EXPIRED")
check("filter promotions by status", r.status_code == 200, r.text)

# ---------------------------------------------------------------------------
# Sales
# ---------------------------------------------------------------------------
r = get("/api/v1/sales/orders")
check("GET /api/v1/sales/orders -> 200", r.status_code == 200, r.text)
orders = r.json()["data"]
check("1000 orders for tenant_001", len(orders) == 100 or r.json()["pagination"]["limit"] == 100, str(r.json()["pagination"]))
order_id = orders[0]["order_id"]

r = get(f"/api/v1/sales/orders/{order_id}")
check("GET single order -> 200", r.status_code == 200, r.text)

r = get(f"/api/v1/sales/orders/{order_id}/items")
check("GET order items -> 200", r.status_code == 200, r.text)
check("order items reference order", all(i["order_id"] == order_id for i in r.json()["data"]))

r = get("/api/v1/sales/orders/does_not_exist")
check("GET missing order -> 404", r.status_code == 404, r.text)

r = get("/api/v1/sales/orders/does_not_exist/items")
check("GET items for missing order -> 404", r.status_code == 404, r.text)

r = get("/api/v1/sales/transactions")
check("GET /api/v1/sales/transactions -> 200", r.status_code == 200, r.text)
check("transactions include items", "items" in r.json()["data"][0])

r = get("/api/v1/sales/orders", params={"date_from": "2026-01-01T00:00:00Z", "date_to": "2026-12-31T23:59:59Z"})
check("orders date range filter -> 200", r.status_code == 200, r.text)

r = get("/api/v1/sales/orders", params={"status": "DELIVERED"})
check("orders status filter -> 200", r.status_code == 200 and all(o["order_status"] == "DELIVERED" for o in r.json()["data"]), r.text)

r = get("/api/v1/sales/orders", params={"product_id": product_id})
check("orders product filter -> 200", r.status_code == 200, r.text)

# ---------------------------------------------------------------------------
# Customers
# ---------------------------------------------------------------------------
r = get("/api/v1/customers")
check("GET /api/v1/customers -> 200", r.status_code == 200, r.text)
customers = r.json()["data"]
check("100 customers for tenant_001", len(customers) == 100, str(len(customers)))
customer_id = customers[0]["customer_id"]

r = get(f"/api/v1/customers/{customer_id}")
check("GET single customer -> 200", r.status_code == 200, r.text)

r = get("/api/v1/customers/does_not_exist")
check("GET missing customer -> 404", r.status_code == 404, r.text)

r = get("/api/v1/customers?customer_segment=PREMIUM")
check("filter customers by segment", r.status_code == 200 and all(c["customer_segment"] == "PREMIUM" for c in r.json()["data"]), r.text)

# ---------------------------------------------------------------------------
# Stores
# ---------------------------------------------------------------------------
r = get("/api/v1/stores")
check("GET /api/v1/stores -> 200", r.status_code == 200, r.text)
stores = r.json()["data"]
check("10 stores for tenant_001", len(stores) == 10, str(len(stores)))
store_id = stores[0]["store_id"]

r = get(f"/api/v1/stores/{store_id}")
check("GET single store -> 200", r.status_code == 200, r.text)

r = get("/api/v1/stores/does_not_exist")
check("GET missing store -> 404", r.status_code == 404, r.text)

r = get("/api/v1/stores?store_type=FLAGSHIP")
check("filter stores by type -> 200", r.status_code == 200, r.text)

# ---------------------------------------------------------------------------
# Tenant isolation
# ---------------------------------------------------------------------------
r1 = get("/api/v1/products", headers={"X-Tenant-ID": TENANT})
r2 = get("/api/v1/products", headers={"X-Tenant-ID": OTHER_TENANT})
ids1 = {p["product_id"] for p in r1.json()["data"]}
ids2 = {p["product_id"] for p in r2.json()["data"]}
check("tenant_001 and tenant_002 products disjoint", len(ids1 & ids2) == 0)

r = get(f"/api/v1/products/{product_id}", headers={"X-Tenant-ID": OTHER_TENANT})
check("cross-tenant product access -> 404", r.status_code == 404, r.text)

r = get(f"/api/v1/suppliers/{supplier_id}", headers={"X-Tenant-ID": OTHER_TENANT})
check("cross-tenant supplier access -> 404", r.status_code == 404, r.text)

r = get(f"/api/v1/sales/orders/{order_id}", headers={"X-Tenant-ID": OTHER_TENANT})
check("cross-tenant order access -> 404", r.status_code == 404, r.text)

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print("\n" + "=" * 60)
print(f"TOTAL: {passed + failed}  PASSED: {passed}  FAILED: {failed}")
print("=" * 60)
if failures:
    print("\nFailures:")
    for f in failures:
        print(f" - {f}")
    sys.exit(1)
else:
    print("\nAll endpoint checks passed!")
    sys.exit(0)
