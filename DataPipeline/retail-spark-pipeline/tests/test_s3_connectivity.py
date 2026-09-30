"""S3 connectivity tests (section 49).

Uses a dedicated `test/` prefix in the configured bucket -- never touches the
bronze/silver/gold/quarantine/logs prefixes used by real pipeline runs.
"""

import subprocess
import sys
import uuid
from pathlib import Path

import boto3
import pytest

from src.config.config import get_settings


@pytest.fixture(scope="module")
def settings():
    return get_settings()


def test_s3_bucket_is_reachable(settings):
    s3 = boto3.client("s3", region_name=settings.aws_region)
    s3.head_bucket(Bucket=settings.s3_bucket)


def test_boto3_can_write_and_read_test_prefix(settings):
    s3 = boto3.client("s3", region_name=settings.aws_region)
    key = f"test/pytest_{uuid.uuid4().hex}.json"
    body = b'{"hello": "world"}'

    s3.put_object(Bucket=settings.s3_bucket, Key=key, Body=body)
    try:
        obj = s3.get_object(Bucket=settings.s3_bucket, Key=key)
        assert obj["Body"].read() == body
    finally:
        s3.delete_object(Bucket=settings.s3_bucket, Key=key)


def test_spark_can_write_and_read_parquet_via_s3a():
    """Full S3A round-trip through Spark.

    Runs in a separate process (its own JVM) rather than sharing the
    session-scoped `spark` fixture: only one SparkContext can exist per JVM,
    and stopping a second differently-configured session here would kill the
    shared local-mode fixture used by every other Spark-gated test.
    """
    pytest.importorskip("pyspark")
    project_root = Path(__file__).resolve().parent.parent
    result = subprocess.run(
        [sys.executable, "-m", "tests._s3a_roundtrip_check"],
        cwd=project_root,
        capture_output=True,
        text=True,
        timeout=180,
    )
    combined = result.stdout + result.stderr
    if result.returncode != 0 and "Java" in combined and "S3A round-trip OK" not in combined:
        pytest.skip("Spark/Java not available in this environment")
    # On Windows, Spark's shutdown hook can fail to delete its own temp dir
    # (antivirus/file-lock) and exit non-zero even after a successful write --
    # the printed marker is the authoritative success signal.
    assert "S3A round-trip OK" in combined, combined
