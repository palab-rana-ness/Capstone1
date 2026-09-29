"""Silver-stage validation: required fields (section 26) + business rules (section 28).

Produces a `validation_errors` array<string> column; an empty array means the
record is valid and may proceed to trusted Silver. Non-empty means it must be
quarantined (see quarantine writer in silver_transform.py).
"""

from pyspark.sql import Column, DataFrame
from pyspark.sql import functions as F

REQUIRED_FIELDS: dict[str, list[str]] = {
    "products": ["product_id", "tenant_id", "sku", "product_name", "supplier_id", "unit_price", "cost_price"],
    "sales": ["order_id", "tenant_id", "customer_id", "store_id"],
    "sales_items": ["order_id", "tenant_id", "order_item_id", "product_id", "quantity", "unit_price"],
    "inventory": ["inventory_id", "tenant_id", "product_id", "location_id", "quantity_on_hand"],
    "promotions": [
        "promotion_id",
        "tenant_id",
        "promotion_code",
        "start_date",
        "end_date",
        "discount_type",
        "discount_value",
    ],
    "promotion_products": ["promotion_id", "tenant_id", "product_id"],
    "suppliers": ["supplier_id", "tenant_id", "supplier_code", "supplier_name"],
    "customers": ["customer_id", "tenant_id", "customer_code"],
    "stores": ["store_id", "tenant_id", "store_code"],
    "categories": ["category_id", "tenant_id", "category_name"],
}


def _required_field_checks(dataset: str) -> list[tuple[str, Column]]:
    return [(f"{field} is required", F.col(field).isNull()) for field in REQUIRED_FIELDS.get(dataset, [])]


def _business_rule_checks(dataset: str) -> list[tuple[str, Column]]:
    """Section 28 data-quality rules. Each entry is (error_message, is_invalid_condition)."""
    if dataset == "products":
        return [
            ("unit_price must be >= 0", F.col("unit_price") < 0),
            ("cost_price must be >= 0", F.col("cost_price") < 0),
            ("tax_rate must be between 0 and 100", (F.col("tax_rate") < 0) | (F.col("tax_rate") > 100)),
        ]
    if dataset == "sales_items":
        return [
            ("quantity must be > 0", F.col("quantity") <= 0),
            ("unit_price must be >= 0", F.col("unit_price") < 0),
            ("discount_amount must be >= 0", F.col("discount_amount") < 0),
            ("tax_amount must be >= 0", F.col("tax_amount") < 0),
            ("line_total must be >= 0", F.col("line_total") < 0),
        ]
    if dataset == "inventory":
        return [
            ("quantity_on_hand must be >= 0", F.col("quantity_on_hand") < 0),
            ("quantity_reserved must be >= 0", F.col("quantity_reserved") < 0),
            ("quantity_available must be >= 0", F.col("quantity_available") < 0),
            ("reorder_level must be >= 0", F.col("reorder_level") < 0),
        ]
    if dataset == "promotions":
        return [
            ("discount_value must be >= 0", F.col("discount_value") < 0),
            ("start_date must be <= end_date", F.col("start_date") > F.col("end_date")),
            (
                "percentage discount must be <= 100",
                (F.col("discount_type") == "PERCENTAGE") & (F.col("discount_value") > 100),
            ),
        ]
    if dataset == "suppliers":
        return [("rating must be between 0 and 5", (F.col("rating") < 0) | (F.col("rating") > 5))]
    return []


def add_validation_errors(df: DataFrame, dataset: str) -> DataFrame:
    """Add a `validation_errors` array<string> column (empty array => valid record)."""
    checks = _required_field_checks(dataset) + _business_rule_checks(dataset)
    if not checks:
        return df.withColumn("validation_errors", F.array().cast("array<string>"))

    error_exprs = [F.when(condition, F.lit(message)) for message, condition in checks]
    return df.withColumn("_raw_validation_errors", F.array(*error_exprs)).withColumn(
        "validation_errors",
        F.expr("filter(_raw_validation_errors, x -> x is not null)"),
    ).drop("_raw_validation_errors")


def split_valid_invalid(df: DataFrame) -> tuple[DataFrame, DataFrame]:
    """Split a validated DataFrame into (valid_df, invalid_df) based on validation_errors."""
    valid_df = df.filter(F.size(F.col("validation_errors")) == 0).drop("validation_errors")
    invalid_df = df.filter(F.size(F.col("validation_errors")) > 0)
    return valid_df, invalid_df
