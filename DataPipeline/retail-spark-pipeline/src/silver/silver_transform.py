"""Silver transform: Bronze -> validate/cleanse -> Silver (+ quarantine + quality metrics).

Layer rules enforced here (section 53): schema standardization, type
conversion, null checks, duplicate handling, validation, cleansing, date
normalization, categorical normalization. No business/pricing calculations.
"""

from datetime import date, datetime, timezone
from typing import Any

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F

from src.config.config import Settings
from src.quality.metrics import build_quality_metrics, write_quality_metrics
from src.silver.cleansing import deduplicate, normalize_categoricals, normalize_timestamps
from src.silver.schema import cast_to_schema
from src.silver.validation import add_validation_errors, split_valid_invalid
from src.utils.logger import get_logger

logger = get_logger(__name__)


def _read_bronze(spark: SparkSession, settings: Settings, dataset: str, tenant_id: str) -> DataFrame:
    path = settings.s3_path("bronze", dataset)
    return spark.read.parquet(path).filter(F.col("tenant_id") == tenant_id)


def _write_quarantine(
    invalid_df: DataFrame,
    settings: Settings,
    dataset: str,
    processing_date: str,
) -> None:
    if invalid_df.rdd.isEmpty():
        return
    quarantined = (
        invalid_df.withColumn("validation_error", F.array_join("validation_errors", "; "))
        .drop("validation_errors")
        .withColumn(
            "validation_timestamp",
            F.lit(datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")),
        )
        .withColumn("processing_date", F.lit(processing_date))
    )
    quarantined.write.mode("overwrite").partitionBy("tenant_id", "processing_date").parquet(
        settings.s3_path("quarantine", dataset)
    )


def _write_silver(valid_df: DataFrame, settings: Settings, dataset: str, processing_date: str) -> int:
    silver_df = valid_df.withColumn("processing_date", F.lit(processing_date))
    silver_df.write.mode("overwrite").partitionBy("tenant_id", "processing_date").parquet(
        settings.s3_path("silver", dataset)
    )
    return silver_df.count()


def _empty_metrics(dataset: str, tenant_id: str, pipeline_id: str, run_id: str) -> dict[str, Any]:
    return build_quality_metrics(
        dataset,
        tenant_id,
        pipeline_id,
        run_id,
        input_record_count=0,
        valid_record_count=0,
        invalid_record_count=0,
        duplicate_record_count=0,
        null_violation_count=0,
        business_rule_violation_count=0,
        referential_integrity_failure_count=0,
        output_record_count=0,
        status="SUCCESS",
    )


def _process_one(
    raw_df: DataFrame,
    settings: Settings,
    dataset: str,
    tenant_id: str,
    pipeline_id: str,
    run_id: str,
    processing_date_str: str,
    dedupe_on_updated_at: bool = True,
) -> dict[str, Any]:
    input_count = raw_df.count()
    typed_df = cast_to_schema(raw_df, dataset)

    if dedupe_on_updated_at:
        typed_df = normalize_timestamps(typed_df, dataset)
        typed_df = normalize_categoricals(typed_df, dataset)
        deduped_df, duplicate_count = deduplicate(typed_df, dataset)
    else:
        keys = ["tenant_id"] + [c for c in typed_df.columns if c.endswith("_item_id")]
        deduped_df = typed_df.dropDuplicates(keys) if keys else typed_df
        duplicate_count = typed_df.count() - deduped_df.count()

    deduped_count = input_count - duplicate_count

    validated_df = add_validation_errors(deduped_df, dataset)
    valid_df, invalid_df = split_valid_invalid(validated_df)
    valid_count = valid_df.count()
    invalid_count = deduped_count - valid_count

    output_count = _write_silver(valid_df, settings, dataset, processing_date_str)
    _write_quarantine(invalid_df, settings, dataset, processing_date_str)

    metrics = build_quality_metrics(
        dataset,
        tenant_id,
        pipeline_id,
        run_id,
        input_record_count=input_count,
        valid_record_count=valid_count,
        invalid_record_count=invalid_count,
        duplicate_record_count=duplicate_count,
        null_violation_count=invalid_count,
        business_rule_violation_count=invalid_count,
        referential_integrity_failure_count=0,
        output_record_count=output_count,
        status="SUCCESS",
    )
    write_quality_metrics(settings, tenant_id, run_id, dataset, metrics)
    return metrics


def transform_dataset(
    spark: SparkSession,
    settings: Settings,
    dataset: str,
    tenant_id: str,
    pipeline_id: str,
    run_id: str,
    processing_date: date,
) -> dict[str, Any]:
    """Run the full Bronze -> Silver pipeline for one dataset/tenant."""
    bronze_df = _read_bronze(spark, settings, dataset, tenant_id)
    if bronze_df.rdd.isEmpty():
        metrics = _empty_metrics(dataset, tenant_id, pipeline_id, run_id)
        write_quality_metrics(settings, tenant_id, run_id, dataset, metrics)
        return metrics

    return _process_one(
        bronze_df, settings, dataset, tenant_id, pipeline_id, run_id, processing_date.isoformat()
    )


def transform_sales(
    spark: SparkSession,
    settings: Settings,
    tenant_id: str,
    pipeline_id: str,
    run_id: str,
    processing_date: date,
) -> list[dict[str, Any]]:
    """Special-case: bronze `sales` holds nested order+items (from /sales/transactions).

    Splits into two trusted Silver tables: `sales` (orders) and `sales_items`.
    """
    processing_date_str = processing_date.isoformat()
    bronze_df = _read_bronze(spark, settings, "sales", tenant_id)

    if bronze_df.rdd.isEmpty():
        metrics = [_empty_metrics(name, tenant_id, pipeline_id, run_id) for name in ("sales", "sales_items")]
        for m in metrics:
            write_quality_metrics(settings, tenant_id, run_id, m["dataset"], m)
        return metrics

    orders_raw = bronze_df.drop("items")
    items_raw = bronze_df.select(
        F.explode("items").alias("item"), "pipeline_id", "run_id", "source_system", "ingestion_timestamp"
    ).select("item.*", "pipeline_id", "run_id", "source_system", "ingestion_timestamp")

    orders_metrics = _process_one(
        orders_raw, settings, "sales", tenant_id, pipeline_id, run_id, processing_date_str, dedupe_on_updated_at=True
    )
    items_metrics = _process_one(
        items_raw,
        settings,
        "sales_items",
        tenant_id,
        pipeline_id,
        run_id,
        processing_date_str,
        dedupe_on_updated_at=False,
    )
    return [orders_metrics, items_metrics]
