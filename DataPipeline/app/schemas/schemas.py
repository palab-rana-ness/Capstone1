from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class SupplierSchema(BaseModel):
    supplier_id: str
    tenant_id: str
    supplier_code: str
    supplier_name: str
    contact_email: str
    phone: Optional[str] = None
    country: str
    city: str
    rating: float
    payment_terms: str
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProductSchema(BaseModel):
    product_id: str
    tenant_id: str
    sku: str
    product_name: str
    description: Optional[str] = None
    category_id: str
    category_name: str
    brand: str
    supplier_id: str
    unit_price: float
    cost_price: float
    currency: str
    tax_rate: float
    unit_of_measure: str
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CategorySchema(BaseModel):
    category_id: str
    tenant_id: str
    category_name: str
    description: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class StoreSchema(BaseModel):
    store_id: str
    tenant_id: str
    store_code: str
    store_name: str
    city: str
    state: str
    country: str
    store_type: str
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CustomerSchema(BaseModel):
    customer_id: str
    tenant_id: str
    customer_code: str
    name: str
    city: str
    state: str
    country: str
    customer_segment: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PromotionSchema(BaseModel):
    promotion_id: str
    tenant_id: str
    promotion_code: str
    promotion_name: str
    description: str
    promotion_type: str
    discount_type: str
    discount_value: float
    start_date: datetime
    end_date: datetime
    minimum_quantity: int
    maximum_discount: float
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PromotionProductSchema(BaseModel):
    promotion_id: str
    tenant_id: str
    product_id: str

    class Config:
        from_attributes = True


class SalesOrderItemSchema(BaseModel):
    order_item_id: str
    order_id: str
    tenant_id: str
    product_id: str
    quantity: int
    unit_price: float
    discount_amount: float
    tax_amount: float
    line_total: float

    class Config:
        from_attributes = True


class SalesOrderSchema(BaseModel):
    order_id: str
    tenant_id: str
    customer_id: str
    store_id: str
    order_date: datetime
    order_status: str
    payment_method: str
    currency: str
    total_amount: float
    discount_amount: float
    tax_amount: float
    net_amount: float
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SalesTransactionSchema(BaseModel):
    order_id: str
    tenant_id: str
    customer_id: str
    store_id: str
    order_date: datetime
    order_status: str
    payment_method: str
    currency: str
    total_amount: float
    discount_amount: float
    tax_amount: float
    net_amount: float
    items: list[SalesOrderItemSchema]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class InventorySchema(BaseModel):
    inventory_id: str
    tenant_id: str
    product_id: str
    location_id: str
    location_type: str
    quantity_on_hand: int
    quantity_reserved: int
    quantity_available: int
    reorder_level: int
    reorder_quantity: int
    last_restocked_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TenantSchema(BaseModel):
    tenant_id: str
    tenant_name: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
