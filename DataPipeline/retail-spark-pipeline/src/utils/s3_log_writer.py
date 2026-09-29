"""Writes small JSON log/metric records to S3 (ingestion, quality, pipeline logs).

Uses boto3 directly rather than Spark -- these records are tiny (one dict per
call), so a Spark write per record would be unnecessary overhead.
"""

import json
from datetime import datetime, timezone
from typing import Any

import boto3

from src.config.config import Settings


def write_log_record(
    settings: Settings, log_type: str, tenant_id: str, run_id: str, name: str, record: dict[str, Any]
) -> str:
    """Write one JSON log record under logs/<log_type>/tenant_id=.../run_id=.../<name>_<ts>.json.

    Returns the S3 key written.
    """
    timestamp = datetime.now(timezone.utc).strftime("%H%M%S%f")
    key = f"logs/{log_type}/tenant_id={tenant_id}/run_id={run_id}/{name}_{timestamp}.json"
    s3 = boto3.client("s3", region_name=settings.aws_region)
    s3.put_object(
        Bucket=settings.s3_bucket,
        Key=key,
        Body=json.dumps(record, default=str).encode("utf-8"),
        ContentType="application/json",
    )
    return key
