"""Writes Bronze DataFrames to S3 as partitioned Parquet.

Rerun safety: the SparkSession sets spark.sql.sources.partitionOverwriteMode
to "dynamic" (see utils/spark_session.py), so a write in "overwrite" mode only
replaces the specific tenant_id/ingestion_date partitions present in the
DataFrame being written -- it never wipes the whole dataset.
"""

from pyspark.sql import DataFrame

from src.config.config import Settings


def write_bronze(df: DataFrame, settings: Settings, dataset: str) -> int:
    """Write a Bronze DataFrame partitioned by tenant_id/ingestion_date. Returns row count."""
    path = settings.s3_path("bronze", dataset)
    row_count = df.count()
    (
        df.write.mode("overwrite")
        .partitionBy("tenant_id", "ingestion_date")
        .parquet(path)
    )
    return row_count
