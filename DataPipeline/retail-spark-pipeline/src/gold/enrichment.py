"""Gold enrichment helpers: promotion, inventory and sales enrichment (sections 35-37).

All joins are keyed on (tenant_id, <business_key>) -- never on the business
key alone -- so a cross-tenant join can never occur (sections 9 and 50).
"""

from datetime import date

from pyspark.sql import DataFrame, Window
from pyspark.sql import functions as F


def enrich_with_promotions(
    products_df: DataFrame,
    promotion_products_df: DataFrame,
    promotions_df: DataFrame,
    business_date: date,
) -> DataFrame:
    """Attach the single best-applicable active promotion to each product."""
    business_date_lit = F.lit(business_date.isoformat()).cast("date")

    active_promotions = promotions_df.filter(
        (F.col("status") == "ACTIVE")
        & (F.to_date(F.col("start_date")) <= business_date_lit)
        & (F.to_date(F.col("end_date")) >= business_date_lit)
    )

    promo_product_links = promotion_products_df.join(
        active_promotions,
        on=(promotion_products_df.tenant_id == active_promotions.tenant_id)
        & (promotion_products_df.promotion_id == active_promotions.promotion_id),
        how="inner",
    ).select(
        promotion_products_df.tenant_id,
        promotion_products_df.product_id,
        active_promotions.promotion_id,
        active_promotions.promotion_type,
        active_promotions.discount_type,
        active_promotions.discount_value,
        active_promotions.maximum_discount,
    )

    # A product can match several active promotions -- deterministically keep
    # the one with the highest discount_value (ties broken by promotion_id).
    window = Window.partitionBy("tenant_id", "product_id").orderBy(
        F.col("discount_value").desc(), F.col("promotion_id").asc()
    )
    best_promo = (
        promo_product_links.withColumn("_rn", F.row_number().over(window))
        .filter(F.col("_rn") == 1)
        .drop("_rn")
    )

    enriched = products_df.join(
        best_promo,
        on=(products_df.tenant_id == best_promo.tenant_id) & (products_df.product_id == best_promo.product_id),
        how="left",
    ).select(
        products_df["*"],
        best_promo.promotion_id,
        best_promo.promotion_type,
        best_promo.discount_type,
        best_promo.discount_value,
        best_promo.maximum_discount,
    )

    return enriched.withColumn("promotion_applied", F.col("promotion_id").isNotNull())


def enrich_with_inventory(products_df: DataFrame, inventory_df: DataFrame) -> DataFrame:
    """Attach inventory_available = SUM(quantity_available) per tenant_id+product_id."""
    inventory_agg = inventory_df.groupBy("tenant_id", "product_id").agg(
        F.sum("quantity_available").alias("inventory_available")
    )
    return products_df.join(
        inventory_agg,
        on=(products_df.tenant_id == inventory_agg.tenant_id)
        & (products_df.product_id == inventory_agg.product_id),
        how="left",
    ).select(
        products_df["*"],
        F.coalesce(inventory_agg.inventory_available, F.lit(0)).alias("inventory_available"),
    )


def enrich_sales(sales_orders_df: DataFrame, sales_items_df: DataFrame, products_df: DataFrame) -> DataFrame:
    """Join orders + items + products, aggregated to tenant_id + product_id level."""
    items_with_orders = sales_items_df.join(
        sales_orders_df,
        on=(sales_items_df.tenant_id == sales_orders_df.tenant_id)
        & (sales_items_df.order_id == sales_orders_df.order_id),
        how="inner",
    ).select(
        sales_items_df.tenant_id,
        sales_items_df.product_id,
        sales_items_df.quantity,
        sales_items_df.unit_price,
        sales_items_df.discount_amount,
        sales_items_df.tax_amount,
        sales_items_df.line_total,
    )

    joined = items_with_orders.join(
        products_df,
        on=(items_with_orders.tenant_id == products_df.tenant_id)
        & (items_with_orders.product_id == products_df.product_id),
        how="inner",
    )

    return joined.groupBy(items_with_orders.tenant_id, items_with_orders.product_id).agg(
        F.sum(items_with_orders.quantity).alias("quantity_sold"),
        F.sum(items_with_orders.quantity * items_with_orders.unit_price).alias("gross_amount"),
        F.sum(items_with_orders.discount_amount).alias("discount_amount"),
        F.sum(items_with_orders.line_total).alias("net_amount"),
    )
