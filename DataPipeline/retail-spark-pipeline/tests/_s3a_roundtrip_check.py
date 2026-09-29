"""Standalone S3A round-trip check, run in its own process/JVM by test_s3_connectivity.py.

Exit code 0 = success. Any exception -> non-zero exit with traceback on stderr.
"""

import sys
import uuid

from src.config.config import get_settings
from src.utils.spark_session import build_spark_session


def main() -> int:
    settings = get_settings()
    spark = build_spark_session(settings)
    try:
        path = f"s3a://{settings.s3_bucket}/test/pytest_spark_{uuid.uuid4().hex}/"
        df = spark.createDataFrame([(1, "a"), (2, "b")], ["id", "value"])
        df.write.mode("overwrite").parquet(path)
        result = spark.read.parquet(path).collect()
        assert len(result) == 2
        print("S3A round-trip OK")
        return 0
    finally:
        spark.stop()


if __name__ == "__main__":
    sys.exit(main())
