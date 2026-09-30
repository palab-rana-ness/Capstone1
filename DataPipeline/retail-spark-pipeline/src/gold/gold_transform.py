"""Gold transform: Silver -> Gold orchestration (sections 32, 38, 40-41)."""

from datetime import date, datetime, timezone
from typing import Any

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F

from src.config.config import Settings
from src.gold.enrichment import enrich_sales, enrich_with_inventory
from src.gold.pricing import build_gold_pricing
from src.quality.quality_checks import validate_gold_pricing
from src.utils.logger import get_logger

logger = get_logger(__name__)


def _read_silver(spark: SparkSession, settings: Settings, dataset: str, tenant_id: str) -> DataFrame:
    path = settings.s3_path("silver", dataset)
    return spark.read.parquet(path).filter(F.col("tenant_id") == tenant_id)


def build_gold_product_sales(
    sales_orders_df: DataFrame,
    sales_items_df: DataFrame,
    products_df: DataFrame,
    inventory_df: DataFrame,
    pipeline_id: str,
    run_id: str,
) -> DataFrame:
    """gold_product_sales (section 38): historical sales performance per product.

    average_selling_price = net_revenue / total_quantity_sold (0 when no sales).
    """
    sales_agg = enrich_sales(sales_orders_df, sales_items_df, products_df)
    enriched = products_df.join(
        sales_agg,
        on=(products_df.tenant_id == sales_agg.tenant_id) & (products_df.product_id == sales_agg.product_id),
        how="left",
    ).select(
        products_df.tenant_id,
        products_df.product_id,
        products_df.sku,
        products_df.product_name,
        products_df.category_name,
        F.coalesce(sales_agg.quantity_sold, F.lit(0)).alias("total_quantity_sold"),
        F.coalesce(sales_agg.gross_amount, F.lit(0)).alias("gross_revenue"),
        F.coalesce(sales_agg.discount_amount, F.lit(0)).alias("discount_amount"),
        F.coalesce(sales_agg.net_amount, F.lit(0)).alias("net_revenue"),
    )

    enriched = enrich_with_inventory(enriched, inventory_df)
    transformation_timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    return enriched.withColumn(
        "average_selling_price",
        F.when(
            F.col("total_quantity_sold") > 0, F.col("net_revenue") / F.col("total_quantity_sold")
        ).otherwise(F.lit(0)),
    ).select(
        "tenant_id",
        "product_id",
        "sku",
        "product_name",
        "category_name",
        "total_quantity_sold",
        F.col("gross_revenue").cast("decimal(18,4)").alias("gross_revenue"),
        F.col("discount_amount").cast("decimal(18,4)").alias("discount_amount"),
        F.col("net_revenue").cast("decimal(18,4)").alias("net_revenue"),
        F.col("average_selling_price").cast("decimal(18,4)").alias("average_selling_price"),
        "inventory_available",
        F.lit(pipeline_id).alias("pipeline_id"),
        F.lit(run_id).alias("run_id"),
        F.lit(transformation_timestamp).alias("transformation_timestamp"),
    )


def run_gold_stage(
    spark: SparkSession,
    settings: Settings,
    tenant_id: str,
    pipeline_id: str,
    run_id: str,
    business_date: date,
) -> dict[str, Any]:
    """Read trusted Silver, build both Gold datasets, validate, and write to S3.

    Gold status is only ever SUCCESS if every validate_gold_pricing check
    passes -- an invalid Gold dataset is never published as successful.
    """
    try:
        products_df = _read_silver(spark, settings, "products", tenant_id)
        promotions_df = _read_silver(spark, settings, "promotions", tenant_id)
        promotion_products_df = _read_silver(spark, settings, "promotion_products", tenant_id)
        inventory_df = _read_silver(spark, settings, "inventory", tenant_id)
        sales_orders_df = _read_silver(spark, settings, "sales", tenant_id)
        sales_items_df = _read_silver(spark, settings, "sales_items", tenant_id)

        pricing_df = build_gold_pricing(
            products_df,
            promotion_products_df,
            promotions_df,
            inventory_df,
            sales_orders_df,
            sales_items_df,
            pipeline_id,
            run_id,
            business_date,
        ).cache()

        failures = validate_gold_pricing(pricing_df)
        if failures:
            logger.error("Gold pricing validation failed: %s", failures)
            return {
                "tenant_id": tenant_id,
                "pipeline_id": pipeline_id,
                "run_id": run_id,
                "gold_status": "FAILED",
                "pricing_records": 0,
                "product_sales_records": 0,
                "validation_failures": failures,
            }

        product_sales_df = build_gold_product_sales(
            sales_orders_df, sales_items_df, products_df, inventory_df, pipeline_id, run_id
        )

        business_date_str = business_date.isoformat()
        pricing_out = pricing_df.withColumn("business_date", F.lit(business_date_str))
        product_sales_out = product_sales_df.withColumn("business_date", F.lit(business_date_str))

        pricing_count = pricing_out.count()
        product_sales_count = product_sales_out.count()

        pricing_out.write.mode("overwrite").partitionBy("tenant_id", "business_date").parquet(
            settings.s3_path("gold", "pricing")
        )
        product_sales_out.write.mode("overwrite").partitionBy("tenant_id", "business_date").parquet(
            settings.s3_path("gold", "product_sales")
        )

        return {
            "tenant_id": tenant_id,
            "pipeline_id": pipeline_id,
            "run_id": run_id,
            "gold_status": "SUCCESS",
            "pricing_records": pricing_count,
            "product_sales_records": product_sales_count,
            "validation_failures": [],
        }
    except Exception as exc:  # noqa: BLE001
        logger.exception("Gold stage failed for tenant=%s", tenant_id)
        return {
            "tenant_id": tenant_id,
            "pipeline_id": pipeline_id,
            "run_id": run_id,
            "gold_status": "FAILED",
            "pricing_records": 0,
            "product_sales_records": 0,
            "validation_failures": [str(exc)],
        }
