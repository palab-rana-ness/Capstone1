from datetime import datetime, timedelta
from faker import Faker
from app.config import settings
from app.models.entities import (
    Supplier, Product, Category, Store, Customer, Promotion,
    PromotionProduct, SalesOrder, SalesOrderItem, Inventory, Tenant
)
from app.data.store import data_store
import random


class DataGenerator:
    """Generate realistic deterministic seed data for the retail platform."""
    
    TENANTS = [
        {"tenant_id": "tenant_001", "tenant_name": "RetailMart India"},
        {"tenant_id": "tenant_002", "tenant_name": "SuperStore India"},
        {"tenant_id": "tenant_003", "tenant_name": "QuickBuy India"},
    ]
    
    CATEGORIES = [
        {"id": "cat_electronics", "name": "Electronics"},
        {"id": "cat_clothing", "name": "Clothing"},
        {"id": "cat_home", "name": "Home & Garden"},
        {"id": "cat_sports", "name": "Sports & Outdoors"},
        {"id": "cat_food", "name": "Food & Beverages"},
        {"id": "cat_books", "name": "Books & Media"},
        {"id": "cat_beauty", "name": "Beauty & Personal Care"},
        {"id": "cat_toys", "name": "Toys & Games"},
        {"id": "cat_furniture", "name": "Furniture"},
        {"id": "cat_automotive", "name": "Automotive"},
    ]
    
    STORE_TYPES = ["FLAGSHIP", "STANDARD", "POPUP", "WAREHOUSE"]
    CUSTOMER_SEGMENTS = ["PREMIUM", "REGULAR", "BUDGET", "VIP"]
    PAYMENT_METHODS = ["CASH", "CREDIT_CARD", "DEBIT_CARD", "UPI", "WALLET"]
    PROMOTION_TYPES = ["PRODUCT_DISCOUNT", "CATEGORY_DISCOUNT", "BUY_ONE_GET_ONE", "COUPON"]
    DISCOUNT_TYPES = ["PERCENTAGE", "FIXED_AMOUNT"]
    ORDER_STATUSES = ["PENDING", "CONFIRMED", "SHIPPED", "DELIVERED", "CANCELLED", "RETURNED"]
    PRODUCT_STATUSES = ["ACTIVE", "INACTIVE", "DISCONTINUED"]
    SUPPLIER_STATUSES = ["ACTIVE", "INACTIVE", "SUSPENDED"]
    PROMOTION_STATUSES = ["ACTIVE", "INACTIVE", "EXPIRED", "UPCOMING"]
    LOCATION_TYPES = ["WAREHOUSE", "STORE"]
    
    def __init__(self, seed: int = 42):
        """Initialize generator with a fixed seed for determinism."""
        self.fake = Faker()
        Faker.seed(seed)
        random.seed(seed)
        # Bounded rate (<=10%) of intentionally invalid records, to exercise
        # the downstream pipeline's silver quarantine and gold validation checks.
        self.error_rate = settings.DATA_ERROR_RATE if settings.DATA_ERROR_INJECTION_ENABLED else 0.0

    def _should_inject_error(self) -> bool:
        """Roll the dice for whether the current record should be corrupted."""
        return self.error_rate > 0 and random.random() < self.error_rate
    
    def generate_all_data(self):
        """Generate all seed data."""
        print("Generating seed data...")
        
        # Generate tenants
        for tenant_info in self.TENANTS:
            self._generate_tenant(tenant_info["tenant_id"], tenant_info["tenant_name"])
        
        # Generate data for each tenant
        for tenant_info in self.TENANTS:
            tenant_id = tenant_info["tenant_id"]
            print(f"  Generating data for {tenant_id}...")
            
            self._generate_categories(tenant_id)
            self._generate_suppliers(tenant_id, count=10)
            self._generate_products(tenant_id, count=50)
            self._generate_stores(tenant_id, count=10)
            self._generate_customers(tenant_id, count=100)
            self._generate_promotions(tenant_id, count=50)
            self._generate_inventory(tenant_id)
            self._generate_sales_orders(tenant_id, count=1000)
        
        print("Seed data generation complete!")
    
    def _generate_tenant(self, tenant_id: str, tenant_name: str):
        """Generate a tenant."""
        tenant = Tenant(
            tenant_id=tenant_id,
            tenant_name=tenant_name,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        data_store.tenants[tenant_id] = tenant
    
    def _generate_categories(self, tenant_id: str):
        """Generate categories for a tenant."""
        for cat in self.CATEGORIES:
            category = Category(
                category_id=cat["id"],
                tenant_id=tenant_id,
                category_name=cat["name"],
                description=self.fake.sentence(nb_words=10),
                status="ACTIVE",
                created_at=datetime.utcnow() - timedelta(days=random.randint(30, 365)),
                updated_at=datetime.utcnow()
            )
            data_store.categories[f"{tenant_id}_{cat['id']}"] = category
    
    def _generate_suppliers(self, tenant_id: str, count: int = 10):
        """Generate suppliers for a tenant."""
        for i in range(count):
            supplier_id = f"sup_{tenant_id[-3:]}_{i+1:03d}"
            supplier = Supplier(
                supplier_id=supplier_id,
                tenant_id=tenant_id,
                supplier_code=f"SUP-{i+1:04d}",
                supplier_name=self.fake.company(),
                contact_email=self.fake.email(),
                phone=self.fake.phone_number() if random.random() > 0.1 else None,
                country="India",
                city=self.fake.city(),
                rating=self._maybe_bad_rating(round(random.uniform(2.5, 5.0), 2)),
                payment_terms=f"{random.choice([15, 30, 45, 60])} days",
                status=random.choice(["ACTIVE", "INACTIVE"]),
                created_at=datetime.utcnow() - timedelta(days=random.randint(30, 365)),
                updated_at=datetime.utcnow()
            )
            data_store.suppliers[supplier_id] = supplier

    def _maybe_bad_rating(self, rating: float) -> float:
        """Occasionally push rating outside the valid 0-5 range (violates suppliers business rule).

        Stays within Decimal(3,2) precision (max 9.99) so Silver casting doesn't hard-crash;
        the out-of-range value is instead caught and quarantined by the business-rule check.
        """
        if self._should_inject_error():
            return round(random.choice([-1 * rating, random.uniform(6.0, 9.99)]), 2)
        return rating

    def _generate_products(self, tenant_id: str, count: int = 50):
        """Generate products for a tenant."""
        suppliers = data_store.get_tenant_suppliers(tenant_id)
        categories = data_store.get_tenant_categories(tenant_id)
        
        if not suppliers or not categories:
            return
        
        for i in range(count):
            product_id = f"prod_{tenant_id[-3:]}_{i+1:05d}"
            supplier = random.choice(suppliers)
            category = random.choice(categories)
            cost = random.uniform(100, 5000)
            unit_price = round(cost * random.uniform(1.3, 2.0), 2)
            cost_price = round(cost, 2)
            tax_rate = random.choice([5, 12, 18])

            if self._should_inject_error():
                defect = random.choice(["negative_unit_price", "negative_cost_price", "invalid_tax_rate"])
                if defect == "negative_unit_price":
                    unit_price = round(-abs(unit_price), 2)
                elif defect == "negative_cost_price":
                    cost_price = round(-abs(cost_price), 2)
                else:
                    tax_rate = random.choice([-5, 150])

            product = Product(
                product_id=product_id,
                tenant_id=tenant_id,
                sku=f"SKU-{i+1:06d}",
                product_name=self.fake.word() + " " + self.fake.word(),
                description=self.fake.sentence(nb_words=15) if random.random() > 0.1 else None,
                category_id=category.category_id,
                category_name=category.category_name,
                brand=self.fake.company(),
                supplier_id=supplier.supplier_id,
                unit_price=unit_price,
                cost_price=cost_price,
                currency="INR",
                tax_rate=tax_rate,
                unit_of_measure=random.choice(["piece", "box", "carton", "kg"]),
                status=random.choice(self.PRODUCT_STATUSES),
                created_at=datetime.utcnow() - timedelta(days=random.randint(30, 365)),
                updated_at=datetime.utcnow()
            )
            data_store.products[product_id] = product
    
    def _generate_stores(self, tenant_id: str, count: int = 10):
        """Generate stores for a tenant."""
        for i in range(count):
            store_id = f"store_{tenant_id[-3:]}_{i+1:02d}"
            store = Store(
                store_id=store_id,
                tenant_id=tenant_id,
                store_code=f"STR-{i+1:03d}",
                store_name=f"{self.fake.city()} Store",
                city=self.fake.city(),
                state=self.fake.state(),
                country="India",
                store_type=random.choice(self.STORE_TYPES),
                status=random.choice(["ACTIVE", "INACTIVE"]),
                created_at=datetime.utcnow() - timedelta(days=random.randint(30, 365)),
                updated_at=datetime.utcnow()
            )
            data_store.stores[store_id] = store
    
    def _generate_customers(self, tenant_id: str, count: int = 100):
        """Generate customers for a tenant."""
        for i in range(count):
            customer_id = f"cust_{tenant_id[-3:]}_{i+1:05d}"
            customer = Customer(
                customer_id=customer_id,
                tenant_id=tenant_id,
                customer_code=f"CUST-{i+1:06d}",
                name=self.fake.name(),
                city=self.fake.city(),
                state=self.fake.state(),
                country="India",
                customer_segment=random.choice(self.CUSTOMER_SEGMENTS),
                created_at=datetime.utcnow() - timedelta(days=random.randint(30, 365)),
                updated_at=datetime.utcnow()
            )
            data_store.customers[customer_id] = customer
    
    def _generate_promotions(self, tenant_id: str, count: int = 50):
        """Generate promotions and promotion-product relationships."""
        products = data_store.get_tenant_products(tenant_id)
        if not products:
            return
        
        for i in range(count):
            promotion_id = f"promo_{tenant_id[-3:]}_{i+1:04d}"
            discount_type = random.choice(self.DISCOUNT_TYPES)
            discount_value = random.uniform(10, 50) if discount_type == "PERCENTAGE" else random.uniform(100, 1000)
            
            start_date = datetime.utcnow() - timedelta(days=random.randint(0, 30))
            end_date = start_date + timedelta(days=random.randint(7, 90))
            status = self._get_promotion_status(start_date, end_date)

            if self._should_inject_error():
                defect = random.choice(["negative_discount", "inverted_dates", "percentage_over_100"])
                if defect == "negative_discount":
                    discount_value = -abs(discount_value)
                elif defect == "inverted_dates":
                    start_date, end_date = end_date, start_date
                elif defect == "percentage_over_100" and discount_type == "PERCENTAGE":
                    discount_value = random.uniform(101, 200)

            promotion = Promotion(
                promotion_id=promotion_id,
                tenant_id=tenant_id,
                promotion_code=f"PROMO{i+1:04d}",
                promotion_name=f"Promotion {i+1}",
                description=self.fake.sentence(nb_words=12),
                promotion_type=random.choice(self.PROMOTION_TYPES),
                discount_type=discount_type,
                discount_value=round(discount_value, 2),
                start_date=start_date,
                end_date=end_date,
                minimum_quantity=random.randint(1, 5),
                maximum_discount=round(random.uniform(500, 5000), 2),
                status=status,
                created_at=start_date - timedelta(days=1),
                updated_at=datetime.utcnow()
            )
            data_store.promotions[promotion_id] = promotion
            
            # Link promotion to random products
            num_products = random.randint(1, min(10, len(products)))
            for _ in range(num_products):
                product = random.choice(products)
                promo_prod = PromotionProduct(
                    promotion_id=promotion_id,
                    tenant_id=tenant_id,
                    product_id=product.product_id
                )
                data_store.promotion_products.append(promo_prod)
    
    def _get_promotion_status(self, start_date: datetime, end_date: datetime) -> str:
        """Determine promotion status based on dates."""
        now = datetime.utcnow()
        if now < start_date:
            return "UPCOMING"
        elif now > end_date:
            return "EXPIRED"
        else:
            return "ACTIVE"
    
    def _generate_inventory(self, tenant_id: str):
        """Generate inventory records for products at locations."""
        products = data_store.get_tenant_products(tenant_id)
        stores = data_store.get_tenant_stores(tenant_id)
        
        if not products or not stores:
            return
        
        # One warehouse for each tenant
        warehouse_id = f"WH_{tenant_id[-3:].upper()}_001"
        
        # Generate inventory for all products at warehouse and stores
        locations = [(warehouse_id, "WAREHOUSE")] + [(s.store_id, "STORE") for s in stores]
        
        inventory_counter = 0
        for product in products:
            for location_id, location_type in locations:
                inventory_id = f"inv_{tenant_id[-3:]}_{inventory_counter:06d}"
                inventory_counter += 1
                
                qoh = random.randint(10, 500)
                qr = random.randint(0, qoh // 2)
                reorder_level = random.randint(20, 100)

                if self._should_inject_error():
                    defect = random.choice(["negative_on_hand", "negative_reserved", "negative_reorder_level"])
                    if defect == "negative_on_hand":
                        qoh = -abs(qoh)
                    elif defect == "negative_reserved":
                        qr = -abs(qr) or -1
                    else:
                        reorder_level = -abs(reorder_level) or -1

                inventory = Inventory(
                    inventory_id=inventory_id,
                    tenant_id=tenant_id,
                    product_id=product.product_id,
                    location_id=location_id,
                    location_type=location_type,
                    quantity_on_hand=qoh,
                    quantity_reserved=qr,
                    quantity_available=qoh - qr,
                    reorder_level=reorder_level,
                    reorder_quantity=random.randint(50, 200),
                    last_restocked_at=datetime.utcnow() - timedelta(days=random.randint(1, 30)),
                    updated_at=datetime.utcnow()
                )
                data_store.inventory[inventory_id] = inventory
    
    def _generate_sales_orders(self, tenant_id: str, count: int = 1000):
        """Generate sales orders and order items."""
        customers = data_store.get_tenant_customers(tenant_id)
        stores = data_store.get_tenant_stores(tenant_id)
        products = data_store.get_tenant_products(tenant_id)
        
        if not customers or not stores or not products:
            return
        
        order_counter = 0
        item_counter = 0
        
        for i in range(count):
            order_id = f"ord_{tenant_id[-3:]}_{i+1:06d}"
            customer = random.choice(customers)
            store = random.choice(stores)
            order_date = datetime.utcnow() - timedelta(days=random.randint(0, 90))
            
            order = SalesOrder(
                order_id=order_id,
                tenant_id=tenant_id,
                customer_id=customer.customer_id,
                store_id=store.store_id,
                order_date=order_date,
                order_status=random.choice(self.ORDER_STATUSES),
                payment_method=random.choice(self.PAYMENT_METHODS),
                currency="INR",
                total_amount=0.0,  # Will be calculated
                discount_amount=0.0,
                tax_amount=0.0,
                net_amount=0.0,
                created_at=order_date,
                updated_at=datetime.utcnow()
            )
            
            # Generate order items
            num_items = random.randint(1, 5)
            total = 0.0
            discount = 0.0
            tax = 0.0
            
            for j in range(num_items):
                order_item_id = f"oi_{tenant_id[-3:]}_{item_counter:08d}"
                item_counter += 1
                
                product = random.choice(products)
                quantity = random.randint(1, 10)
                unit_price = product.unit_price
                item_discount = round(unit_price * quantity * random.uniform(0, 0.2), 2)
                item_tax = round((unit_price * quantity - item_discount) * (product.tax_rate / 100), 2)
                line_total = unit_price * quantity - item_discount + item_tax

                if self._should_inject_error():
                    defect = random.choice([
                        "non_positive_quantity", "negative_unit_price",
                        "discount_exceeds_gross", "negative_line_total",
                    ])
                    if defect == "non_positive_quantity":
                        quantity = random.choice([0, -1 * quantity])
                    elif defect == "negative_unit_price":
                        unit_price = round(-abs(unit_price), 2)
                    elif defect == "discount_exceeds_gross":
                        item_discount = round((unit_price * quantity) + random.uniform(50, 500), 2)
                    else:
                        line_total = round(-abs(line_total) - 1, 2)

                order_item = SalesOrderItem(
                    order_item_id=order_item_id,
                    order_id=order_id,
                    tenant_id=tenant_id,
                    product_id=product.product_id,
                    quantity=quantity,
                    unit_price=round(unit_price, 2),
                    discount_amount=item_discount,
                    tax_amount=item_tax,
                    line_total=round(line_total, 2)
                )
                data_store.sales_order_items.append(order_item)
                
                total += unit_price * quantity
                discount += item_discount
                tax += item_tax
            
            order.total_amount = round(total, 2)
            order.discount_amount = round(discount, 2)
            order.tax_amount = round(tax, 2)
            order.net_amount = round(total - discount + tax, 2)
            
            data_store.sales_orders[order_id] = order


def init_seed_data():
    """Initialize seed data for the application."""
    generator = DataGenerator(seed=42)
    generator.generate_all_data()
