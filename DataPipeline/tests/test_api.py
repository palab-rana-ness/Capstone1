import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.data.store import data_store
from app.data.seed import init_seed_data

client = TestClient(app)

# Setup
@pytest.fixture(scope="session", autouse=True)
def setup_data():
    """Initialize seed data once for all tests."""
    init_seed_data()
    yield


class TestHealth:
    """Test health endpoint."""
    
    def test_health_check(self):
        """Test health endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "retail-mock-data-service"


class TestTenants:
    """Test tenant endpoints."""
    
    def test_list_tenants(self):
        """Test listing all tenants."""
        response = client.get("/api/v1/tenants")
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "metadata" in data
        assert "pagination" in data
        assert len(data["data"]) >= 3  # At least 3 tenants


class TestProductsWithoutTenant:
    """Test that endpoints require X-Tenant-ID header."""
    
    def test_missing_tenant_header(self):
        """Test that missing X-Tenant-ID returns 400."""
        response = client.get("/api/v1/products")
        assert response.status_code == 400
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "MISSING_TENANT_ID"
    
    def test_invalid_tenant_id(self):
        """Test that invalid X-Tenant-ID returns 400."""
        response = client.get(
            "/api/v1/products",
            headers={"X-Tenant-ID": "invalid_tenant"}
        )
        assert response.status_code == 400
        data = response.json()
        assert data["error"]["code"] == "INVALID_TENANT_ID"


class TestProducts:
    """Test product endpoints."""
    
    tenant_id = "tenant_001"
    
    def test_list_products(self):
        """Test listing products."""
        response = client.get(
            "/api/v1/products",
            headers={"X-Tenant-ID": self.tenant_id}
        )
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert len(data["data"]) > 0
        assert data["metadata"]["tenant_id"] == self.tenant_id
        assert data["metadata"]["source_system"] == "product_database"
    
    def test_get_single_product(self):
        """Test getting a single product."""
        # Get first product from list
        products = data_store.get_tenant_products(self.tenant_id)
        if not products:
            pytest.skip("No products available")
        
        product_id = products[0].product_id
        response = client.get(
            f"/api/v1/products/{product_id}",
            headers={"X-Tenant-ID": self.tenant_id}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["product_id"] == product_id
        assert data["data"]["tenant_id"] == self.tenant_id
    
    def test_product_not_found(self):
        """Test 404 for non-existent product."""
        response = client.get(
            "/api/v1/products/nonexistent_product",
            headers={"X-Tenant-ID": self.tenant_id}
        )
        assert response.status_code == 404
        data = response.json()
        assert data["error"]["code"] == "RESOURCE_NOT_FOUND"
    
    def test_filter_by_category(self):
        """Test filtering products by category."""
        categories = data_store.get_tenant_categories(self.tenant_id)
        if not categories:
            pytest.skip("No categories available")
        
        category_id = categories[0].category_id
        response = client.get(
            f"/api/v1/products?category_id={category_id}",
            headers={"X-Tenant-ID": self.tenant_id}
        )
        assert response.status_code == 200
        data = response.json()
        if data["data"]:
            assert all(p["category_id"] == category_id for p in data["data"])
    
    def test_pagination(self):
        """Test pagination."""
        response = client.get(
            "/api/v1/products?limit=10&offset=0",
            headers={"X-Tenant-ID": self.tenant_id}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["pagination"]["limit"] == 10
        assert data["pagination"]["offset"] == 0
        assert len(data["data"]) <= 10


class TestSuppliers:
    """Test supplier endpoints."""
    
    tenant_id = "tenant_001"
    
    def test_list_suppliers(self):
        """Test listing suppliers."""
        response = client.get(
            "/api/v1/suppliers",
            headers={"X-Tenant-ID": self.tenant_id}
        )
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert len(data["data"]) > 0
        assert data["metadata"]["source_system"] == "supplier_api"
    
    def test_get_single_supplier(self):
        """Test getting a single supplier."""
        suppliers = data_store.get_tenant_suppliers(self.tenant_id)
        if not suppliers:
            pytest.skip("No suppliers available")
        
        supplier_id = suppliers[0].supplier_id
        response = client.get(
            f"/api/v1/suppliers/{supplier_id}",
            headers={"X-Tenant-ID": self.tenant_id}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["supplier_id"] == supplier_id


class TestInventory:
    """Test inventory endpoints."""
    
    tenant_id = "tenant_001"
    
    def test_list_inventory(self):
        """Test listing inventory."""
        response = client.get(
            "/api/v1/inventory",
            headers={"X-Tenant-ID": self.tenant_id}
        )
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert data["metadata"]["source_system"] == "inventory_api"
    
    def test_get_inventory_by_product(self):
        """Test getting inventory by product."""
        products = data_store.get_tenant_products(self.tenant_id)
        if not products:
            pytest.skip("No products available")
        
        product_id = products[0].product_id
        response = client.get(
            f"/api/v1/inventory/product/{product_id}",
            headers={"X-Tenant-ID": self.tenant_id}
        )
        assert response.status_code == 200
        data = response.json()
        if data["data"]:
            assert all(inv["product_id"] == product_id for inv in data["data"])
    
    def test_filter_low_stock(self):
        """Test filtering low stock inventory."""
        response = client.get(
            "/api/v1/inventory?low_stock=true",
            headers={"X-Tenant-ID": self.tenant_id}
        )
        assert response.status_code == 200
        data = response.json()
        if data["data"]:
            for inv in data["data"]:
                assert inv["quantity_available"] <= inv["reorder_level"]


class TestPromotions:
    """Test promotion endpoints."""
    
    tenant_id = "tenant_001"
    
    def test_list_promotions(self):
        """Test listing promotions."""
        response = client.get(
            "/api/v1/promotions",
            headers={"X-Tenant-ID": self.tenant_id}
        )
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert data["metadata"]["source_system"] == "promotion_api"
    
    def test_get_active_promotions(self):
        """Test getting active promotions."""
        response = client.get(
            "/api/v1/promotions/active",
            headers={"X-Tenant-ID": self.tenant_id}
        )
        assert response.status_code == 200
        data = response.json()
        if data["data"]:
            assert all(p["status"] == "ACTIVE" for p in data["data"])
    
    def test_get_product_promotions(self):
        """Test getting promotions for a product."""
        products = data_store.get_tenant_products(self.tenant_id)
        if not products:
            pytest.skip("No products available")
        
        product_id = products[0].product_id
        response = client.get(
            f"/api/v1/products/{product_id}/promotions",
            headers={"X-Tenant-ID": self.tenant_id}
        )
        assert response.status_code == 200
        data = response.json()
        assert "data" in data


class TestSales:
    """Test sales endpoints."""
    
    tenant_id = "tenant_001"
    
    def test_list_sales_orders(self):
        """Test listing sales orders."""
        response = client.get(
            "/api/v1/sales/orders",
            headers={"X-Tenant-ID": self.tenant_id}
        )
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert len(data["data"]) > 0
        assert data["metadata"]["source_system"] == "sales_database"
    
    def test_get_sales_order(self):
        """Test getting a single sales order."""
        orders = data_store.get_tenant_sales_orders(self.tenant_id)
        if not orders:
            pytest.skip("No orders available")
        
        order_id = orders[0].order_id
        response = client.get(
            f"/api/v1/sales/orders/{order_id}",
            headers={"X-Tenant-ID": self.tenant_id}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["order_id"] == order_id
    
    def test_get_sales_order_items(self):
        """Test getting items for a sales order."""
        orders = data_store.get_tenant_sales_orders(self.tenant_id)
        if not orders:
            pytest.skip("No orders available")
        
        order_id = orders[0].order_id
        response = client.get(
            f"/api/v1/sales/orders/{order_id}/items",
            headers={"X-Tenant-ID": self.tenant_id}
        )
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        if data["data"]:
            assert all(item["order_id"] == order_id for item in data["data"])
    
    def test_get_sales_transactions(self):
        """Test getting sales transactions."""
        response = client.get(
            "/api/v1/sales/transactions",
            headers={"X-Tenant-ID": self.tenant_id}
        )
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        if data["data"]:
            assert "items" in data["data"][0]


class TestTenantIsolation:
    """Test tenant isolation."""
    
    def test_tenant_001_cannot_see_tenant_002_products(self):
        """Test that tenant_001 cannot see tenant_002 products."""
        tenant_001_response = client.get(
            "/api/v1/products",
            headers={"X-Tenant-ID": "tenant_001"}
        )
        tenant_001_products = [p["product_id"] for p in tenant_001_response.json()["data"]]
        
        tenant_002_response = client.get(
            "/api/v1/products",
            headers={"X-Tenant-ID": "tenant_002"}
        )
        tenant_002_products = [p["product_id"] for p in tenant_002_response.json()["data"]]
        
        # Should have different product sets
        assert len(set(tenant_001_products) & set(tenant_002_products)) == 0
    
    def test_tenant_001_cannot_access_tenant_002_supplier(self):
        """Test that tenant_001 cannot access tenant_002 supplier."""
        suppliers_002 = data_store.get_tenant_suppliers("tenant_002")
        if not suppliers_002:
            pytest.skip("No suppliers for tenant_002")
        
        supplier_id = suppliers_002[0].supplier_id
        response = client.get(
            f"/api/v1/suppliers/{supplier_id}",
            headers={"X-Tenant-ID": "tenant_001"}
        )
        assert response.status_code == 404


class TestUpdatedSinceFiltering:
    """Test updated_since filtering for CDC."""
    
    tenant_id = "tenant_001"
    
    def test_products_updated_since(self):
        """Test products with updated_since filter."""
        from datetime import datetime, timedelta
        
        # Get products updated since yesterday
        yesterday = (datetime.utcnow() - timedelta(days=1)).isoformat() + "Z"
        response = client.get(
            f"/api/v1/products?updated_since={yesterday}",
            headers={"X-Tenant-ID": self.tenant_id}
        )
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
    
    def test_inventory_updated_since(self):
        """Test inventory with updated_since filter."""
        from datetime import datetime, timedelta
        
        yesterday = (datetime.utcnow() - timedelta(days=1)).isoformat() + "Z"
        response = client.get(
            f"/api/v1/inventory?updated_since={yesterday}",
            headers={"X-Tenant-ID": self.tenant_id}
        )
        assert response.status_code == 200
        data = response.json()
        assert "data" in data


class TestCustomers:
    """Test customer endpoints."""
    
    tenant_id = "tenant_001"
    
    def test_list_customers(self):
        """Test listing customers."""
        response = client.get(
            "/api/v1/customers",
            headers={"X-Tenant-ID": self.tenant_id}
        )
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert len(data["data"]) > 0


class TestStores:
    """Test store endpoints."""
    
    tenant_id = "tenant_001"
    
    def test_list_stores(self):
        """Test listing stores."""
        response = client.get(
            "/api/v1/stores",
            headers={"X-Tenant-ID": self.tenant_id}
        )
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert len(data["data"]) > 0


class TestDataRelationships:
    """Test that data relationships are maintained."""
    
    tenant_id = "tenant_001"
    
    def test_product_has_valid_supplier(self):
        """Test that products reference valid suppliers."""
        products = data_store.get_tenant_products(self.tenant_id)
        suppliers = data_store.get_tenant_suppliers(self.tenant_id)
        supplier_ids = [s.supplier_id for s in suppliers]
        
        for product in products:
            assert product.supplier_id in supplier_ids
    
    def test_order_items_reference_valid_products(self):
        """Test that order items reference valid products."""
        orders = data_store.get_tenant_sales_orders(self.tenant_id)
        if not orders:
            pytest.skip("No orders")
        
        products = data_store.get_tenant_products(self.tenant_id)
        product_ids = [p.product_id for p in products]
        
        items = data_store.sales_order_items
        for item in items:
            if item.tenant_id == self.tenant_id:
                assert item.product_id in product_ids
