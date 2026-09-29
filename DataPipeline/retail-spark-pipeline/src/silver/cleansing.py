"""Silver-stage cleansing: timestamp/categorical normalization and dedup (section 29)."""

from pyspark.sql import DataFrame, Window
from pyspark.sql import functions as F

BUSINESS_KEYS: dict[str, list[str]] = {
    "products": ["tenant_id", "product_id"],
    "sales": ["tenant_id", "order_id"],
    "sales_items": ["tenant_id", "order_item_id"],
    "inventory": ["tenant_id", "inventory_id"],
    "promotions": ["tenant_id", "promotion_id"],
    "promotion_products": ["tenant_id", "promotion_id", "product_id"],
    "suppliers": ["tenant_id", "supplier_id"],
    "customers": ["tenant_id", "customer_id"],
    "stores": ["tenant_id", "store_id"],
    "categories": ["tenant_id", "category_id"],
}

# Status/categorical fields normalized to trimmed upper-case for consistency.
CATEGORICAL_FIELDS: dict[str, list[str]] = {
    "products": ["status", "currency", "unit_of_measure"],
    "sales": ["order_status", "payment_method", "currency"],
    "inventory": ["location_type"],
    "promotions": ["promotion_type", "discount_type", "status"],
    "suppliers": ["status"],
    "customers": ["customer_segment"],
    "stores": ["store_type", "status"],
    "categories": ["status"],
}

TIMESTAMP_FIELDS: dict[str, list[str]] = {
    "products": ["created_at", "updated_at"],
    "sales": ["order_date", "created_at", "updated_at"],
    "inventory": ["last_restocked_at", "updated_at"],
    "promotions": ["start_date", "end_date", "created_at", "updated_at"],
    "suppliers": ["created_at", "updated_at"],
    "customers": ["created_at", "updated_at"],
    "stores": ["created_at", "updated_at"],
    "categories": ["created_at", "updated_at"],
}


def normalize_timestamps(df: DataFrame, dataset: str) -> DataFrame:
    """Standardize timestamp-like columns into TimestampType (UTC session timezone)."""
    for field in TIMESTAMP_FIELDS.get(dataset, []):
        if field in df.columns:
            df = df.withColumn(field, F.to_timestamp(F.col(field)))
    return df


def normalize_categoricals(df: DataFrame, dataset: str) -> DataFrame:
    """Trim + uppercase categorical/status-like fields for consistency."""
    for field in CATEGORICAL_FIELDS.get(dataset, []):
        if field in df.columns:
            df = df.withColumn(field, F.upper(F.trim(F.col(field))))
    return df


def deduplicate(df: DataFrame, dataset: str, order_col: str = "updated_at") -> tuple[DataFrame, int]:
    """Keep only the latest record per business key. Returns (deduped_df, duplicate_count)."""
    keys = BUSINESS_KEYS.get(dataset)
    if not keys or order_col not in df.columns:
        return df, 0

    input_count = df.count()
    window = Window.partitionBy(*keys).orderBy(F.col(order_col).desc_nulls_last())
    deduped_df = df.withColumn("_rn", F.row_number().over(window)).filter(F.col("_rn") == 1).drop("_rn")
    duplicate_count = input_count - deduped_df.count()
    return deduped_df, duplicate_count
