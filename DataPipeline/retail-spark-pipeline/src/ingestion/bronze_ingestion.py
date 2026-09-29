"""Bronze ingestion: FastAPI -> Spark DataFrame (+ metadata) -> S3 Bronze.

Bronze responsibility (strict, see README "Layer rules"): stay close to the
source. Allowed: serialization, metadata tagging, ingestion timestamp, source
identification, basic schema compatibility. NOT allowed: business
calculations, pricing logic, revenue/margin calculations, aggregation.
"""

from datetime import datetime, timezone
from typing import Any, Optional

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F

from src.bronze.bronze_writer import write_bronze
from src.config.config import Settings
from src.ingestion.api_client import RetailAPIClient
from src.ingestion.paginator import fetch_all_records
from src.utils.logger import get_logger

logger = get_logger(__name__)


def _iso(dt: datetime) -> str:
    return dt.isoformat().replace("+00:00", "Z")


def _with_bronze_metadata(
    df: DataFrame,
    tenant_id: str,
    pipeline_id: str,
    run_id: str,
    source_system: str,
    ingestion_timestamp: str,
) -> DataFrame:
    """Attach mandatory Bronze traceability columns.

    tenant_id is always overwritten with the X-Tenant-ID-validated value used
    to make the API call -- a tenant_id field inside the response body is
    never trusted for partitioning/isolation.
    """
    return (
        df.withColumn("tenant_id", F.lit(tenant_id))
        .withColumn("pipeline_id", F.lit(pipeline_id))
        .withColumn("run_id", F.lit(run_id))
        .withColumn("source_system", F.lit(source_system))
        .withColumn("ingestion_timestamp", F.lit(ingestion_timestamp))
        .withColumn("ingestion_date", F.lit(ingestion_timestamp[:10]))
    )


def _empty_log(
    pipeline_id: str, run_id: str, tenant_id: str, dataset: str, source_system: str, start_time: datetime
) -> dict[str, Any]:
    return {
        "pipeline_id": pipeline_id,
        "run_id": run_id,
        "tenant_id": tenant_id,
        "dataset": dataset,
        "source_system": source_system,
        "start_time": _iso(start_time),
        "end_time": _iso(start_time),
        "records_received": 0,
        "records_written": 0,
        "status": "SUCCESS",
        "error_message": None,
    }


def ingest_dataset(
    spark: SparkSession,
    settings: Settings,
    dataset: str,
    tenant_id: str,
    pipeline_id: str,
    run_id: str,
    mode: str,
    updated_since: Optional[str],
) -> dict[str, Any]:
    """Ingest a single dataset for a single tenant from FastAPI into S3 Bronze.

    Returns an ingestion log record matching the schema in README section 21.
    """
    endpoint = settings.endpoint_for(dataset)
    path = endpoint["path"]
    source_system = endpoint["source_system"]

    start_time = datetime.now(timezone.utc)
    log = _empty_log(pipeline_id, run_id, tenant_id, dataset, source_system, start_time)

    client = RetailAPIClient(settings, tenant_id)
    try:
        effective_updated_since = updated_since if mode == "incremental" else None
        records = fetch_all_records(
            client=client,
            path=path,
            page_size=settings.api_page_size,
            updated_since=effective_updated_since,
        )
        log["records_received"] = len(records)

        if records:
            raw_df = spark.createDataFrame(records)
            ingestion_ts = _iso(start_time)
            bronze_df = _with_bronze_metadata(
                raw_df, tenant_id, pipeline_id, run_id, source_system, ingestion_ts
            )
            log["records_written"] = write_bronze(bronze_df, settings, dataset)
        else:
            logger.info("No records returned for dataset=%s tenant=%s", dataset, tenant_id)

    except Exception as exc:  # noqa: BLE001 -- captured into the ingestion log, not swallowed silently
        log["status"] = "FAILED"
        log["error_message"] = str(exc)
        logger.exception("Bronze ingestion failed for dataset=%s tenant=%s", dataset, tenant_id)
    finally:
        client.close()

    log["end_time"] = _iso(datetime.now(timezone.utc))
    return log


def ingest_promotion_products(
    spark: SparkSession,
    settings: Settings,
    tenant_id: str,
    pipeline_id: str,
    run_id: str,
    product_ids: list[str],
) -> dict[str, Any]:
    """Derive the promotion<->product relationship dataset.

    The FastAPI source has no bulk endpoint for this relationship, only
    GET /api/v1/products/{product_id}/promotions. This calls it once per
    already-ingested product to build the promotion_products Bronze dataset.
    """
    dataset = "promotion_products"
    source_system = "promotion_api"
    start_time = datetime.now(timezone.utc)
    log = _empty_log(pipeline_id, run_id, tenant_id, dataset, source_system, start_time)
    records: list[dict[str, Any]] = []

    client = RetailAPIClient(settings, tenant_id)
    try:
        for product_id in product_ids:
            envelope = client.get_single(f"/api/v1/products/{product_id}/promotions")
            for promo in envelope.get("data", []):
                records.append({"product_id": product_id, "promotion_id": promo["promotion_id"]})

        log["records_received"] = len(records)
        if records:
            raw_df = spark.createDataFrame(records)
            ingestion_ts = _iso(start_time)
            bronze_df = _with_bronze_metadata(
                raw_df, tenant_id, pipeline_id, run_id, source_system, ingestion_ts
            )
            log["records_written"] = write_bronze(bronze_df, settings, dataset)
    except Exception as exc:  # noqa: BLE001
        log["status"] = "FAILED"
        log["error_message"] = str(exc)
        logger.exception("promotion_products ingestion failed for tenant=%s", tenant_id)
    finally:
        client.close()

    log["end_time"] = _iso(datetime.now(timezone.utc))
    return log
