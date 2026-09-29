"""Pipeline orchestrator: FastAPI -> S3 Bronze -> S3 Silver -> S3 Gold.

One run_id is generated once here and threaded through every stage so any
Gold record can be traced back to the exact pipeline execution that produced
it (section 10/11).
"""

import argparse
import sys
from datetime import datetime, timezone

from observability.telemetry import build_telemetry
from src.config.config import get_settings
from src.gold.gold_transform import run_gold_stage
from src.ingestion.bronze_ingestion import ingest_dataset, ingest_promotion_products
from src.silver.silver_transform import transform_dataset, transform_sales
from src.utils.logger import get_logger
from src.utils.run_id import generate_run_id
from src.utils.s3_log_writer import write_log_record
from src.utils.spark_session import build_spark_session

logger = get_logger(__name__)


def _duration_seconds(start_iso: str, end_iso: str) -> float:
    start = datetime.fromisoformat(start_iso.replace("Z", "+00:00"))
    end = datetime.fromisoformat(end_iso.replace("Z", "+00:00"))
    return max(0.0, round((end - start).total_seconds(), 4))


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Retail AWS data pipeline (FastAPI -> S3 Bronze/Silver/Gold)")
    parser.add_argument("--tenant-id", required=True, help="tenant_001, tenant_002, tenant_003, or 'all'")
    parser.add_argument("--mode", choices=["full", "incremental"], default="full")
    parser.add_argument(
        "--updated-since",
        default=None,
        help="ISO-8601 timestamp, required when --mode incremental (e.g. 2026-09-24T00:00:00Z)",
    )
    args = parser.parse_args(argv)
    if args.mode == "incremental" and not args.updated_since:
        parser.error("--updated-since is required when --mode incremental")
    return args


def _print_header(pipeline_id: str, run_id: str, tenant_id: str, mode: str, bucket: str) -> None:
    print("=" * 41)
    print("RETAIL AWS DATA PIPELINE")
    print("=" * 41)
    print(f"\nPipeline ID:\n{pipeline_id}")
    print(f"\nRun ID:\n{run_id}")
    print(f"\nTenant:\n{tenant_id}")
    print(f"\nMode:\n{mode.upper()}")
    print(f"\nS3 Bucket:\n{bucket}\n")


def run_for_tenant(spark, settings, tenant_id: str, mode: str, updated_since: str | None) -> dict:
    run_id = generate_run_id()
    pipeline_id = settings.pipeline_id
    business_date = datetime.now(timezone.utc).date()
    telemetry = build_telemetry(settings, run_id=run_id, tenant_id=tenant_id)
    pipeline_start = telemetry.stage_timer()

    _print_header(pipeline_id, run_id, tenant_id, mode, settings.s3_bucket)
    telemetry.log_event(
        "PIPELINE_START",
        "INFO",
        "Pipeline execution started",
        stage="pipeline",
        dataset="pipeline",
        status="RUNNING",
        mode=mode,
        processing_date=business_date.isoformat(),
    )
    telemetry.record_metric("pipeline_run_count", 1, stage="pipeline", dataset="pipeline")

    # ---------------- Stage 1: FastAPI -> S3 Bronze ----------------
    print("[1/3] FASTAPI -> S3 BRONZE\n")
    bronze_stage_start = telemetry.stage_timer()
    telemetry.log_event(
        "BRONZE_START",
        "INFO",
        "Bronze ingestion stage started",
        stage="bronze",
        dataset="all",
        status="RUNNING",
    )
    ingestion_logs = []
    for dataset in settings.all_datasets:
        telemetry.log_event(
            "BRONZE_START",
            "INFO",
            "Bronze ingestion started for dataset",
            stage="bronze",
            dataset=dataset,
            status="RUNNING",
            source_system=settings.endpoint_for(dataset).get("source_system"),
        )
        log = ingest_dataset(spark, settings, dataset, tenant_id, pipeline_id, run_id, mode, updated_since)
        ingestion_logs.append(log)
        write_log_record(settings, "ingestion", tenant_id, run_id, dataset, log)

        duration = _duration_seconds(log["start_time"], log["end_time"])
        telemetry.record_metric("bronze_records_ingested", log["records_received"], stage="bronze", dataset=dataset)
        telemetry.record_metric("bronze_records_written", log["records_written"], stage="bronze", dataset=dataset)
        telemetry.record_metric("api_request_count", 1, stage="bronze", dataset=dataset)
        telemetry.record_metric("api_request_duration_seconds", duration, stage="bronze", dataset=dataset)
        telemetry.record_metric("s3_write_duration_seconds", duration, stage="bronze", dataset=dataset)

        if log["status"] == "SUCCESS":
            telemetry.log_event(
                "BRONZE_END",
                "INFO",
                "Bronze ingestion completed for dataset",
                stage="bronze",
                dataset=dataset,
                status="SUCCESS",
                source_system=log.get("source_system"),
                records_received=log.get("records_received", 0),
                records_written=log.get("records_written", 0),
                processing_time_seconds=duration,
            )
        else:
            telemetry.record_metric("api_error_count", 1, stage="bronze", dataset=dataset)
            telemetry.log_event(
                "BRONZE_FAILURE",
                "ERROR",
                "Bronze ingestion failed for dataset",
                stage="bronze",
                dataset=dataset,
                status="FAILED",
                source_system=log.get("source_system"),
                error_type="API_FAILURE",
                error_message=log.get("error_message"),
            )
            telemetry.log_event(
                "API_FAILURE",
                "ERROR",
                "Source API ingestion failure",
                stage="bronze",
                dataset=dataset,
                status="FAILED",
                error_type="API_FAILURE",
                error_message=log.get("error_message"),
            )
        label = dataset.replace("_", " ").title()
        print(f"{label + ':':<14}{log['records_written']}")

    products_log = next((l for l in ingestion_logs if l["dataset"] == "products"), None)
    if products_log and products_log["status"] == "SUCCESS" and products_log["records_written"] > 0:
        telemetry.log_event(
            "BRONZE_START",
            "INFO",
            "Bronze ingestion started for derived dataset",
            stage="bronze",
            dataset="promotion_products",
            status="RUNNING",
            source_system="promotion_api",
        )
        product_ids = _read_bronze_product_ids(spark, settings, tenant_id)
        promo_products_log = ingest_promotion_products(spark, settings, tenant_id, pipeline_id, run_id, product_ids)
        ingestion_logs.append(promo_products_log)
        write_log_record(settings, "ingestion", tenant_id, run_id, "promotion_products", promo_products_log)
        promo_duration = _duration_seconds(promo_products_log["start_time"], promo_products_log["end_time"])
        telemetry.record_metric("bronze_records_ingested", promo_products_log["records_received"], stage="bronze", dataset="promotion_products")
        telemetry.record_metric("bronze_records_written", promo_products_log["records_written"], stage="bronze", dataset="promotion_products")
        telemetry.record_metric("api_request_count", 1, stage="bronze", dataset="promotion_products")
        telemetry.record_metric("api_request_duration_seconds", promo_duration, stage="bronze", dataset="promotion_products")
        telemetry.record_metric("s3_write_duration_seconds", promo_duration, stage="bronze", dataset="promotion_products")
        if promo_products_log["status"] == "SUCCESS":
            telemetry.log_event(
                "BRONZE_END",
                "INFO",
                "Bronze ingestion completed for derived dataset",
                stage="bronze",
                dataset="promotion_products",
                status="SUCCESS",
                records_received=promo_products_log.get("records_received", 0),
                records_written=promo_products_log.get("records_written", 0),
                processing_time_seconds=promo_duration,
            )
        else:
            telemetry.record_metric("api_error_count", 1, stage="bronze", dataset="promotion_products")
            telemetry.log_event(
                "BRONZE_FAILURE",
                "ERROR",
                "Bronze ingestion failed for derived dataset",
                stage="bronze",
                dataset="promotion_products",
                status="FAILED",
                error_type="API_FAILURE",
                error_message=promo_products_log.get("error_message"),
            )
            telemetry.log_event(
                "API_FAILURE",
                "ERROR",
                "Source API ingestion failure for derived dataset",
                stage="bronze",
                dataset="promotion_products",
                status="FAILED",
                error_type="API_FAILURE",
                error_message=promo_products_log.get("error_message"),
            )
        print(f"{'Promotion Links:':<14}{promo_products_log['records_written']}")

    bronze_status = "SUCCESS" if all(l["status"] == "SUCCESS" for l in ingestion_logs) else "FAILED"
    telemetry.record_metric("bronze_duration_seconds", telemetry.stage_elapsed(bronze_stage_start), stage="bronze", dataset="all")
    telemetry.log_event(
        "BRONZE_END" if bronze_status == "SUCCESS" else "BRONZE_FAILURE",
        "INFO" if bronze_status == "SUCCESS" else "ERROR",
        "Bronze stage completed" if bronze_status == "SUCCESS" else "Bronze stage failed",
        stage="bronze",
        dataset="all",
        status=bronze_status,
    )
    print(f"\nStatus: {bronze_status}\n")

    # ---------------- Stage 2: S3 Bronze -> S3 Silver ----------------
    print("[2/3] S3 BRONZE -> S3 SILVER\n")
    silver_stage_start = telemetry.stage_timer()
    telemetry.log_event(
        "SILVER_START",
        "INFO",
        "Silver transform stage started",
        stage="silver",
        dataset="all",
        status="RUNNING",
    )
    silver_metrics = []
    silver_status = "SUCCESS"
    silver_quality_failures: list[str] = []
    try:
        for dataset in [d for d in settings.all_datasets if d != "sales"] + ["promotion_products"]:
            telemetry.log_event(
                "SILVER_START",
                "INFO",
                "Silver transformation started for dataset",
                stage="silver",
                dataset=dataset,
                status="RUNNING",
            )
            m = transform_dataset(spark, settings, dataset, tenant_id, pipeline_id, run_id, business_date)
            silver_metrics.append(m)
            telemetry.record_metric("silver_input_records", m["input_record_count"], stage="silver", dataset=dataset)
            telemetry.record_metric("silver_valid_records", m["valid_record_count"], stage="silver", dataset=dataset)
            telemetry.record_metric("silver_invalid_records", m["invalid_record_count"], stage="silver", dataset=dataset)
            telemetry.record_metric("silver_duplicate_records", m["duplicate_record_count"], stage="silver", dataset=dataset)
            telemetry.record_metric("silver_quarantine_records", m["invalid_record_count"], stage="silver", dataset=dataset)
            telemetry.record_metric("input_record_count", m["input_record_count"], stage="silver", dataset=dataset)
            telemetry.record_metric("valid_record_count", m["valid_record_count"], stage="silver", dataset=dataset)
            telemetry.record_metric("invalid_record_count", m["invalid_record_count"], stage="silver", dataset=dataset)
            telemetry.record_metric("duplicate_record_count", m["duplicate_record_count"], stage="silver", dataset=dataset)
            telemetry.record_metric("null_violation_count", m["null_violation_count"], stage="silver", dataset=dataset)
            telemetry.record_metric(
                "business_rule_violation_count",
                m["business_rule_violation_count"],
                stage="silver",
                dataset=dataset,
            )
            telemetry.record_metric(
                "referential_integrity_failure_count",
                m["referential_integrity_failure_count"],
                stage="silver",
                dataset=dataset,
            )
            telemetry.record_metric("quarantine_record_count", m["invalid_record_count"], stage="silver", dataset=dataset)

            if m["invalid_record_count"] > 0:
                invalid_rate = m["invalid_record_count"] / max(1, m["input_record_count"])
                telemetry.log_event(
                    "QUARANTINE_RECORDS",
                    "WARNING",
                    "Records moved to quarantine",
                    stage="silver",
                    dataset=dataset,
                    status="SUCCESS",
                    invalid_records=m["invalid_record_count"],
                    input_records=m["input_record_count"],
                    invalid_rate=round(invalid_rate, 4),
                )
                telemetry.log_event(
                    "DATA_QUALITY_FAILURE",
                    "WARNING",
                    "Silver data-quality checks found invalid records",
                    stage="silver",
                    dataset=dataset,
                    status="FAILED",
                    invalid_records=m["invalid_record_count"],
                    duplicate_records=m["duplicate_record_count"],
                )
                if invalid_rate > settings.silver_invalid_rate_threshold:
                    silver_quality_failures.append(
                        f"{dataset}: invalid rate {invalid_rate:.2%} exceeds threshold "
                        f"{settings.silver_invalid_rate_threshold:.0%} "
                        f"({m['invalid_record_count']}/{m['input_record_count']} records quarantined)"
                    )

            telemetry.log_event(
                "SILVER_END",
                "INFO",
                "Silver transformation completed for dataset",
                stage="silver",
                dataset=dataset,
                status=m.get("status", "SUCCESS"),
                input_records=m["input_record_count"],
                valid_records=m["valid_record_count"],
                invalid_records=m["invalid_record_count"],
                duplicate_records=m["duplicate_record_count"],
            )

        sales_metrics = transform_sales(spark, settings, tenant_id, pipeline_id, run_id, business_date)
        silver_metrics.extend(sales_metrics)
        for m in sales_metrics:
            dataset = m["dataset"]
            telemetry.record_metric("silver_input_records", m["input_record_count"], stage="silver", dataset=dataset)
            telemetry.record_metric("silver_valid_records", m["valid_record_count"], stage="silver", dataset=dataset)
            telemetry.record_metric("silver_invalid_records", m["invalid_record_count"], stage="silver", dataset=dataset)
            telemetry.record_metric("silver_duplicate_records", m["duplicate_record_count"], stage="silver", dataset=dataset)
            telemetry.record_metric("silver_quarantine_records", m["invalid_record_count"], stage="silver", dataset=dataset)
            telemetry.record_metric("input_record_count", m["input_record_count"], stage="silver", dataset=dataset)
            telemetry.record_metric("valid_record_count", m["valid_record_count"], stage="silver", dataset=dataset)
            telemetry.record_metric("invalid_record_count", m["invalid_record_count"], stage="silver", dataset=dataset)
            telemetry.record_metric("duplicate_record_count", m["duplicate_record_count"], stage="silver", dataset=dataset)
            telemetry.record_metric("null_violation_count", m["null_violation_count"], stage="silver", dataset=dataset)
            telemetry.record_metric(
                "business_rule_violation_count",
                m["business_rule_violation_count"],
                stage="silver",
                dataset=dataset,
            )
            telemetry.record_metric(
                "referential_integrity_failure_count",
                m["referential_integrity_failure_count"],
                stage="silver",
                dataset=dataset,
            )
            telemetry.record_metric("quarantine_record_count", m["invalid_record_count"], stage="silver", dataset=dataset)
            if m["invalid_record_count"] > 0:
                invalid_rate = m["invalid_record_count"] / max(1, m["input_record_count"])
                telemetry.log_event(
                    "QUARANTINE_RECORDS",
                    "WARNING",
                    "Records moved to quarantine",
                    stage="silver",
                    dataset=dataset,
                    status="SUCCESS",
                    invalid_records=m["invalid_record_count"],
                    input_records=m["input_record_count"],
                    invalid_rate=round(invalid_rate, 4),
                )
                telemetry.log_event(
                    "DATA_QUALITY_FAILURE",
                    "WARNING",
                    "Silver data-quality checks found invalid records",
                    stage="silver",
                    dataset=dataset,
                    status="FAILED",
                    invalid_records=m["invalid_record_count"],
                    duplicate_records=m["duplicate_record_count"],
                )
                if invalid_rate > settings.silver_invalid_rate_threshold:
                    silver_quality_failures.append(
                        f"{dataset}: invalid rate {invalid_rate:.2%} exceeds threshold "
                        f"{settings.silver_invalid_rate_threshold:.0%} "
                        f"({m['invalid_record_count']}/{m['input_record_count']} records quarantined)"
                    )
            telemetry.log_event(
                "SILVER_END",
                "INFO",
                "Silver transformation completed for dataset",
                stage="silver",
                dataset=dataset,
                status=m.get("status", "SUCCESS"),
                input_records=m["input_record_count"],
                valid_records=m["valid_record_count"],
                invalid_records=m["invalid_record_count"],
                duplicate_records=m["duplicate_record_count"],
            )

        for m in silver_metrics:
            label = m["dataset"].replace("_", " ").title()
            print(f"{label}:\nInput: {m['input_record_count']}\nValid: {m['valid_record_count']}\nInvalid: {m['invalid_record_count']}\n")

        if silver_quality_failures:
            silver_status = "FAILED"
            telemetry.log_event(
                "DATA_QUALITY_THRESHOLD_EXCEEDED",
                "ERROR",
                "Silver invalid-record rate exceeded threshold for one or more datasets",
                stage="silver",
                dataset="all",
                status="FAILED",
                error_type="DATA_QUALITY_THRESHOLD_EXCEEDED",
                failure_reasons=silver_quality_failures,
            )
    except Exception:  # noqa: BLE001
        logger.exception("Silver stage failed for tenant=%s", tenant_id)
        silver_status = "FAILED"
        telemetry.log_event(
            "SILVER_FAILURE",
            "ERROR",
            "Silver stage failed",
            stage="silver",
            dataset="all",
            status="FAILED",
            error_type="S3_READ_FAILURE",
        )
        telemetry.log_event(
            "S3_READ_FAILURE",
            "ERROR",
            "Silver stage failed while reading/writing S3",
            stage="silver",
            dataset="all",
            status="FAILED",
            error_type="S3_READ_FAILURE",
        )

    silver_duration = telemetry.stage_elapsed(silver_stage_start)
    telemetry.record_metric("silver_duration_seconds", silver_duration, stage="silver", dataset="all")
    telemetry.log_event(
        "SILVER_END" if silver_status == "SUCCESS" else "SILVER_FAILURE",
        "INFO" if silver_status == "SUCCESS" else "ERROR",
        "Silver stage completed" if silver_status == "SUCCESS" else "Silver stage failed",
        stage="silver",
        dataset="all",
        status=silver_status,
        processing_time_seconds=silver_duration,
    )

    print(f"Status: {silver_status}\n")
    if silver_quality_failures:
        print("Data-quality threshold breaches:")
        for reason in silver_quality_failures:
            print(f"  - {reason}")
        print()

    # ---------------- Stage 3: S3 Silver -> S3 Gold ----------------
    print("[3/3] S3 SILVER -> S3 GOLD\n")
    gold_stage_start = telemetry.stage_timer()
    telemetry.log_event(
        "GOLD_START",
        "INFO",
        "Gold transformation stage started",
        stage="gold",
        dataset="all",
        status="RUNNING",
    )
    gold_result = run_gold_stage(spark, settings, tenant_id, pipeline_id, run_id, business_date)
    gold_duration = telemetry.stage_elapsed(gold_stage_start)
    telemetry.record_metric("gold_duration_seconds", gold_duration, stage="gold", dataset="all")
    telemetry.record_metric("gold_output_records", gold_result.get("pricing_records", 0), stage="gold", dataset="pricing")
    telemetry.record_metric(
        "gold_output_records",
        gold_result.get("product_sales_records", 0),
        stage="gold",
        dataset="product_sales",
    )
    telemetry.record_metric(
        "gold_input_records",
        sum(m.get("valid_record_count", 0) for m in silver_metrics),
        stage="gold",
        dataset="all",
    )
    telemetry.record_metric(
        "gold_validation_failures",
        len(gold_result.get("validation_failures", [])),
        stage="gold",
        dataset="pricing",
    )
    print(f"Pricing records: {gold_result['pricing_records']}")
    print(f"Product sales records: {gold_result['product_sales_records']}\n")
    print(f"Status: {gold_result['gold_status']}\n")

    if gold_result["gold_status"] == "SUCCESS":
        telemetry.log_event(
            "GOLD_END",
            "INFO",
            "Gold transformation completed",
            stage="gold",
            dataset="all",
            status="SUCCESS",
            pricing_records=gold_result.get("pricing_records", 0),
            product_sales_records=gold_result.get("product_sales_records", 0),
            processing_time_seconds=gold_duration,
        )
    else:
        telemetry.log_event(
            "GOLD_FAILURE",
            "ERROR",
            "Gold transformation failed",
            stage="gold",
            dataset="all",
            status="FAILED",
            error_type="GOLD_VALIDATION_FAILURE",
            validation_failures=gold_result.get("validation_failures", []),
        )
        telemetry.log_event(
            "S3_WRITE_FAILURE",
            "ERROR",
            "Gold stage could not publish output datasets",
            stage="gold",
            dataset="all",
            status="FAILED",
            error_type="S3_WRITE_FAILURE",
        )

    overall_status = (
        "SUCCESS" if bronze_status == "SUCCESS" and silver_status == "SUCCESS" and gold_result["gold_status"] == "SUCCESS" else "FAILED"
    )

    pipeline_status = {
        "pipeline_id": pipeline_id,
        "run_id": run_id,
        "tenant_id": tenant_id,
        "bronze_status": bronze_status,
        "silver_status": silver_status,
        "gold_status": gold_result["gold_status"],
        "overall_status": overall_status,
        "silver_quality_failures": silver_quality_failures,
        "gold_validation_failures": gold_result.get("validation_failures", []),
    }
    write_log_record(settings, "pipeline", tenant_id, run_id, "pipeline_status", pipeline_status)

    pipeline_duration = telemetry.stage_elapsed(pipeline_start)
    telemetry.record_metric("pipeline_duration_seconds", pipeline_duration, stage="pipeline", dataset="pipeline")
    if overall_status == "SUCCESS":
        telemetry.record_metric("pipeline_success_count", 1, stage="pipeline", dataset="pipeline")
        telemetry.log_event(
            "PIPELINE_END",
            "INFO",
            "Pipeline execution completed",
            stage="pipeline",
            dataset="pipeline",
            status="SUCCESS",
            bronze_status=bronze_status,
            silver_status=silver_status,
            gold_status=gold_result["gold_status"],
            processing_time_seconds=pipeline_duration,
        )
    else:
        telemetry.record_metric("pipeline_failure_count", 1, stage="pipeline", dataset="pipeline")
        telemetry.log_event(
            "PIPELINE_FAILURE",
            "ERROR",
            "Pipeline execution failed",
            stage="pipeline",
            dataset="pipeline",
            status="FAILED",
            bronze_status=bronze_status,
            silver_status=silver_status,
            gold_status=gold_result["gold_status"],
            processing_time_seconds=pipeline_duration,
        )

    print("=" * 41)
    print("PIPELINE COMPLETED")
    print("=" * 41)
    print(f"\nOverall Status: {overall_status}\n")
    if overall_status == "FAILED":
        for reason in silver_quality_failures:
            print(f"  - {reason}")
        for reason in gold_result.get("validation_failures", []):
            print(f"  - gold pricing: {reason}")

    telemetry.shutdown()

    return pipeline_status


def _read_bronze_product_ids(spark, settings, tenant_id: str) -> list[str]:
    from pyspark.sql import functions as F

    df = spark.read.parquet(settings.s3_path("bronze", "products")).filter(F.col("tenant_id") == tenant_id)
    return [row["product_id"] for row in df.select("product_id").distinct().collect()]


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])
    settings = get_settings()

    tenants = settings.all_tenants if args.tenant_id == "all" else [args.tenant_id]

    spark = build_spark_session(settings)
    try:
        results = [run_for_tenant(spark, settings, tenant_id, args.mode, args.updated_since) for tenant_id in tenants]
    finally:
        spark.stop()

    return 0 if all(r["overall_status"] == "SUCCESS" for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
