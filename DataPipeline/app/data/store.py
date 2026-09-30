from datetime import datetime, timedelta
from typing import Optional
from app.models.entities import (
    Supplier, Product, Category, Store, Customer, Promotion,
    PromotionProduct, SalesOrder, SalesOrderItem, Inventory, Tenant
)


class DataStore:
    """In-memory data store for all retail data."""
    
    def __init__(self):
        self.suppliers: dict[str, Supplier] = {}
        self.products: dict[str, Product] = {}
        self.categories: dict[str, Category] = {}
        self.stores: dict[str, Store] = {}
        self.customers: dict[str, Customer] = {}
        self.promotions: dict[str, Promotion] = {}
        self.promotion_products: list[PromotionProduct] = []
        self.sales_orders: dict[str, SalesOrder] = {}
        self.sales_order_items: list[SalesOrderItem] = []
        self.inventory: dict[str, Inventory] = {}
        self.tenants: dict[str, Tenant] = {}
    
    def get_tenant_suppliers(self, tenant_id: str) -> list[Supplier]:
        """Get all suppliers for a tenant."""
        return [s for s in self.suppliers.values() if s.tenant_id == tenant_id]
    
    def get_tenant_products(self, tenant_id: str) -> list[Product]:
        """Get all products for a tenant."""
        return [p for p in self.products.values() if p.tenant_id == tenant_id]
    
    def get_tenant_categories(self, tenant_id: str) -> list[Category]:
        """Get all categories for a tenant."""
        return [c for c in self.categories.values() if c.tenant_id == tenant_id]
    
    def get_tenant_stores(self, tenant_id: str) -> list[Store]:
        """Get all stores for a tenant."""
        return [s for s in self.stores.values() if s.tenant_id == tenant_id]
    
    def get_tenant_customers(self, tenant_id: str) -> list[Customer]:
        """Get all customers for a tenant."""
        return [c for c in self.customers.values() if c.tenant_id == tenant_id]
    
    def get_tenant_promotions(self, tenant_id: str) -> list[Promotion]:
        """Get all promotions for a tenant."""
        return [p for p in self.promotions.values() if p.tenant_id == tenant_id]
    
    def get_tenant_sales_orders(self, tenant_id: str) -> list[SalesOrder]:
        """Get all sales orders for a tenant."""
        return [so for so in self.sales_orders.values() if so.tenant_id == tenant_id]
    
    def get_tenant_inventory(self, tenant_id: str) -> list[Inventory]:
        """Get all inventory for a tenant."""
        return [inv for inv in self.inventory.values() if inv.tenant_id == tenant_id]
    
    def get_sales_order_items_for_order(self, order_id: str, tenant_id: str) -> list[SalesOrderItem]:
        """Get all items for a specific sales order."""
        return [item for item in self.sales_order_items 
                if item.order_id == order_id and item.tenant_id == tenant_id]
    
    def get_promotions_for_product(self, product_id: str, tenant_id: str) -> list[Promotion]:
        """Get all active promotions for a product."""
        promo_ids = [pp.promotion_id for pp in self.promotion_products 
                     if pp.product_id == product_id and pp.tenant_id == tenant_id]
        return [p for p in self.promotions.values() 
                if p.promotion_id in promo_ids and p.tenant_id == tenant_id]
    
    def get_inventory_for_product(self, product_id: str, tenant_id: str) -> list[Inventory]:
        """Get all inventory records for a product."""
        return [inv for inv in self.inventory.values() 
                if inv.product_id == product_id and inv.tenant_id == tenant_id]
    
    def get_inventory_for_location(self, location_id: str, tenant_id: str) -> list[Inventory]:
        """Get all inventory records for a location."""
        return [inv for inv in self.inventory.values() 
                if inv.location_id == location_id and inv.tenant_id == tenant_id]
    
    def get_supplier(self, supplier_id: str, tenant_id: str) -> Optional[Supplier]:
        """Get a specific supplier."""
        supplier = self.suppliers.get(supplier_id)
        if supplier and supplier.tenant_id == tenant_id:
            return supplier
        return None
    
    def get_product(self, product_id: str, tenant_id: str) -> Optional[Product]:
        """Get a specific product."""
        product = self.products.get(product_id)
        if product and product.tenant_id == tenant_id:
            return product
        return None
    
    def get_sales_order(self, order_id: str, tenant_id: str) -> Optional[SalesOrder]:
        """Get a specific sales order."""
        order = self.sales_orders.get(order_id)
        if order and order.tenant_id == tenant_id:
            return order
        return None
    
    def get_promotion(self, promotion_id: str, tenant_id: str) -> Optional[Promotion]:
        """Get a specific promotion."""
        promo = self.promotions.get(promotion_id)
        if promo and promo.tenant_id == tenant_id:
            return promo
        return None
    
    def get_customer(self, customer_id: str, tenant_id: str) -> Optional[Customer]:
        """Get a specific customer."""
        customer = self.customers.get(customer_id)
        if customer and customer.tenant_id == tenant_id:
            return customer
        return None
    
    def get_store(self, store_id: str, tenant_id: str) -> Optional[Store]:
        """Get a specific store."""
        store = self.stores.get(store_id)
        if store and store.tenant_id == tenant_id:
            return store
        return None
    
    def get_category(self, category_id: str, tenant_id: str) -> Optional[Category]:
        """Get a specific category."""
        category = self.categories.get(category_id)
        if category and category.tenant_id == tenant_id:
            return category
        return None


# Global data store instance
data_store = DataStore()
