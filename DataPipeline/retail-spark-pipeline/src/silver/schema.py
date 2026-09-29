"""Explicit PySpark schemas for the Silver layer (section 25).

Schema-on-write, not inferred: every trusted Silver dataset is cast to these
exact types before validation and cleansing.
"""

from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from pyspark.sql.types import (
    DecimalType,
    IntegerType,
    StringType,
    StructField,
    StructType,
    TimestampType,
)

MONEY = DecimalType(18, 4)
RATE = DecimalType(5, 2)
RATING = DecimalType(3, 2)

SILVER_SCHEMAS: dict[str, StructType] = {
    "products": StructType(
        [
            StructField("product_id", StringType()),
            StructField("tenant_id", StringType()),
            StructField("sku", StringType()),
            StructField("product_name", StringType()),
            StructField("description", StringType()),
            StructField("category_id", StringType()),
            StructField("category_name", StringType()),
            StructField("brand", StringType()),
            StructField("supplier_id", StringType()),
            StructField("unit_price", MONEY),
            StructField("cost_price", MONEY),
            StructField("currency", StringType()),
            StructField("tax_rate", RATE),
            StructField("unit_of_measure", StringType()),
            StructField("status", StringType()),
            StructField("created_at", TimestampType()),
            StructField("updated_at", TimestampType()),
        ]
    ),
    "sales": StructType(
        [
            StructField("order_id", StringType()),
            StructField("tenant_id", StringType()),
            StructField("customer_id", StringType()),
            StructField("store_id", StringType()),
            StructField("order_date", TimestampType()),
            StructField("order_status", StringType()),
            StructField("payment_method", StringType()),
            StructField("currency", StringType()),
            StructField("total_amount", MONEY),
            StructField("discount_amount", MONEY),
            StructField("tax_amount", MONEY),
            StructField("net_amount", MONEY),
            StructField("created_at", TimestampType()),
            StructField("updated_at", TimestampType()),
        ]
    ),
    "sales_items": StructType(
        [
            StructField("order_item_id", StringType()),
            StructField("order_id", StringType()),
            StructField("tenant_id", StringType()),
            StructField("product_id", StringType()),
            StructField("quantity", IntegerType()),
            StructField("unit_price", MONEY),
            StructField("discount_amount", MONEY),
            StructField("tax_amount", MONEY),
            StructField("line_total", MONEY),
        ]
    ),
    "inventory": StructType(
        [
            StructField("inventory_id", StringType()),
            StructField("tenant_id", StringType()),
            StructField("product_id", StringType()),
            StructField("location_id", StringType()),
            StructField("location_type", StringType()),
            StructField("quantity_on_hand", IntegerType()),
            StructField("quantity_reserved", IntegerType()),
            StructField("quantity_available", IntegerType()),
            StructField("reorder_level", IntegerType()),
            StructField("reorder_quantity", IntegerType()),
            StructField("last_restocked_at", TimestampType()),
            StructField("updated_at", TimestampType()),
        ]
    ),
    "promotions": StructType(
        [
            StructField("promotion_id", StringType()),
            StructField("tenant_id", StringType()),
            StructField("promotion_code", StringType()),
            StructField("promotion_name", StringType()),
            StructField("description", StringType()),
            StructField("promotion_type", StringType()),
            StructField("discount_type", StringType()),
            StructField("discount_value", MONEY),
            StructField("start_date", TimestampType()),
            StructField("end_date", TimestampType()),
            StructField("minimum_quantity", IntegerType()),
            StructField("maximum_discount", MONEY),
            StructField("status", StringType()),
            StructField("created_at", TimestampType()),
            StructField("updated_at", TimestampType()),
        ]
    ),
    "promotion_products": StructType(
        [
            StructField("promotion_id", StringType()),
            StructField("tenant_id", StringType()),
            StructField("product_id", StringType()),
        ]
    ),
    "suppliers": StructType(
        [
            StructField("supplier_id", StringType()),
            StructField("tenant_id", StringType()),
            StructField("supplier_code", StringType()),
            StructField("supplier_name", StringType()),
            StructField("contact_email", StringType()),
            StructField("phone", StringType()),
            StructField("country", StringType()),
            StructField("city", StringType()),
            StructField("rating", RATING),
            StructField("payment_terms", StringType()),
            StructField("status", StringType()),
            StructField("created_at", TimestampType()),
            StructField("updated_at", TimestampType()),
        ]
    ),
    "customers": StructType(
        [
            StructField("customer_id", StringType()),
            StructField("tenant_id", StringType()),
            StructField("customer_code", StringType()),
            StructField("name", StringType()),
            StructField("city", StringType()),
            StructField("state", StringType()),
            StructField("country", StringType()),
            StructField("customer_segment", StringType()),
            StructField("created_at", TimestampType()),
            StructField("updated_at", TimestampType()),
        ]
    ),
    "stores": StructType(
        [
            StructField("store_id", StringType()),
            StructField("tenant_id", StringType()),
            StructField("store_code", StringType()),
            StructField("store_name", StringType()),
            StructField("city", StringType()),
            StructField("state", StringType()),
            StructField("country", StringType()),
            StructField("store_type", StringType()),
            StructField("status", StringType()),
            StructField("created_at", TimestampType()),
            StructField("updated_at", TimestampType()),
        ]
    ),
    "categories": StructType(
        [
            StructField("category_id", StringType()),
            StructField("tenant_id", StringType()),
            StructField("category_name", StringType()),
            StructField("description", StringType()),
            StructField("status", StringType()),
            StructField("created_at", TimestampType()),
            StructField("updated_at", TimestampType()),
        ]
    ),
}

# Pipeline traceability columns that must survive Bronze -> Silver -> Gold.
TRACE_COLUMNS = ["pipeline_id", "run_id", "source_system", "ingestion_timestamp"]


def cast_to_schema(df: DataFrame, dataset: str) -> DataFrame:
    """Select + cast business columns to the explicit Silver schema, keep trace columns."""
    target_schema = SILVER_SCHEMAS[dataset]
    select_exprs = [
        F.col(field.name).cast(field.dataType).alias(field.name)
        for field in target_schema.fields
        if field.name in df.columns
    ]
    trace_exprs = [F.col(c) for c in TRACE_COLUMNS if c in df.columns]
    return df.select(*select_exprs, *trace_exprs)
