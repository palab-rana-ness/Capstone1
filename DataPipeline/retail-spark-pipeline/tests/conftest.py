"""Shared pytest fixtures.

`spark` builds a local (no S3A) SparkSession for fast unit tests of the
transform logic. Tests using it are automatically skipped in environments
without a JVM (Java) -- see README "Troubleshooting" for setup instructions.
"""

import os
import sys

import pytest

# Same Windows Python-worker fix as src/utils/spark_session.py.
os.environ.setdefault("PYSPARK_PYTHON", sys.executable)
os.environ.setdefault("PYSPARK_DRIVER_PYTHON", sys.executable)


@pytest.fixture(scope="session")
def spark():
    pytest.importorskip("pyspark")
    try:
        from pyspark.sql import SparkSession

        session = (
            SparkSession.builder.master("local[2]")
            .appName("retail-pipeline-tests")
            .config("spark.sql.session.timeZone", "UTC")
            .config("spark.sql.pyspark.inferNestedDictAsStruct.enabled", "true")
            .config("spark.ui.enabled", "false")
            .config("spark.sql.shuffle.partitions", "2")
            .getOrCreate()
        )
    except Exception as exc:  # noqa: BLE001 -- e.g. missing JVM/Java on this machine
        pytest.skip(f"Spark/Java not available in this environment: {exc}")
    yield session
    session.stop()
