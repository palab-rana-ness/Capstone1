"""Gold pricing dataset (gold_pricing, sections 33-34).

Documented formulas:

  unit_discount =
      0                                                            if no active promotion
      MIN(base_price * discount_value / 100, maximum_discount, base_price)   if PERCENTAGE
      MIN(discount_value, maximum_discount, base_price)                      if FIXED_AMOUNT

  final_price = base_price - unit_discount            (per unit, after discount; always >= 0)
  net_price   = final_price * (1 + tax_rate / 100)    (per unit, tax-inclusive)

  gross_amount    = quantity_sold * base_price        (aggregate revenue potential at catalog price)
  discount_amount = quantity_sold * unit_discount      (aggregate discount; always <= gross_amount)
"""

from datetime import date, datetime, timezone

from pyspark.sql import Column, DataFrame
from pyspark.sql import functions as F

from src.gold.enrichment import enrich_sales, enrich_with_inventory, enrich_with_promotions


def _compute_unit_discount() -> Column:
    discount_value = F.coalesce(F.col("discount_value"), F.lit(0))
    max_discount = F.col("maximum_discount")
    base_price = F.col("base_price")

    percentage_discount = base_price * discount_value / F.lit(100)
    raw_discount = (
        F.when(F.col("discount_type") == "PERCENTAGE", percentage_discount)
        .when(F.col("discount_type") == "FIXED_AMOUNT", discount_value)
        .otherwise(F.lit(0))
    )

    capped = F.least(raw_discount, base_price)
    capped = F.when(max_discount.isNotNull(), F.least(capped, max_discount)).otherwise(capped)

    return F.when(F.col("promotion_applied"), capped).otherwise(F.lit(0)).cast("decimal(18,4)")


def build_gold_pricing(
    products_df: DataFrame,
    promotion_products_df: DataFrame,
    promotions_df: DataFrame,
    inventory_df: DataFrame,
    sales_orders_df: DataFrame,
    sales_items_df: DataFrame,
    pipeline_id: str,
    run_id: str,
    business_date: date,
) -> DataFrame:
    enriched = enrich_with_promotions(products_df, promotion_products_df, promotions_df, business_date)
    enriched = enrich_with_inventory(enriched, inventory_df)

    sales_agg = enrich_sales(sales_orders_df, sales_items_df, products_df)
    enriched = enriched.join(
        sales_agg,
        on=(enriched.tenant_id == sales_agg.tenant_id) & (enriched.product_id == sales_agg.product_id),
        how="left",
    ).select(enriched["*"], F.coalesce(sales_agg.quantity_sold, F.lit(0)).alias("quantity_sold"))

    priced = (
        enriched.withColumnRenamed("unit_price", "base_price")
        .withColumn("unit_discount", _compute_unit_discount())
        .withColumn("final_price", F.col("base_price") - F.col("unit_discount"))
        .withColumn("net_price", F.col("final_price") * (F.lit(1) + F.col("tax_rate") / F.lit(100)))
        .withColumn("gross_amount", F.col("quantity_sold") * F.col("base_price"))
        .withColumn("discount_amount", F.col("quantity_sold") * F.col("unit_discount"))
    )

    transformation_timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    return priced.select(
        "tenant_id",
        "product_id",
        "sku",
        "product_name",
        "category_id",
        "category_name",
        "brand",
        "supplier_id",
        "base_price",
        "cost_price",
        "quantity_sold",
        "inventory_available",
        "promotion_applied",
        "promotion_id",
        "promotion_type",
        "discount_type",
        "discount_value",
        F.col("gross_amount").cast("decimal(18,4)").alias("gross_amount"),
        F.col("discount_amount").cast("decimal(18,4)").alias("discount_amount"),
        F.col("final_price").cast("decimal(18,4)").alias("final_price"),
        F.col("net_price").cast("decimal(18,4)").alias("net_price"),
        "currency",
        F.lit(pipeline_id).alias("pipeline_id"),
        F.lit(run_id).alias("run_id"),
        F.lit(transformation_timestamp).alias("transformation_timestamp"),
    )
