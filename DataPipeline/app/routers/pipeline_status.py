"""Exposes the latest retail-spark-pipeline run status, read from its S3 log records."""

import json

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.config import settings
from app.middleware.tenant import validate_tenant_header

router = APIRouter(prefix="/api/v1/pipeline", tags=["pipeline"])


def _latest_run_id(s3, tenant_id: str) -> str:
    """Find the most recent run_id under logs/pipeline/tenant_id=<tenant>/ (run_id is timestamp-sortable)."""
    prefix = f"logs/pipeline/tenant_id={tenant_id}/"
    response = s3.list_objects_v2(Bucket=settings.S3_BUCKET, Prefix=prefix, Delimiter="/")
    run_prefixes = [p["Prefix"] for p in response.get("CommonPrefixes", [])]
    if not run_prefixes:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "NO_PIPELINE_RUNS", "message": f"No pipeline runs found for tenant {tenant_id}"}},
        )
    latest_prefix = sorted(run_prefixes)[-1]
    return latest_prefix[len(prefix):].rstrip("/").removeprefix("run_id=")


def _latest_status_key(s3, tenant_id: str, run_id: str) -> str:
    prefix = f"logs/pipeline/tenant_id={tenant_id}/run_id={run_id}/pipeline_status_"
    response = s3.list_objects_v2(Bucket=settings.S3_BUCKET, Prefix=prefix)
    keys = [obj["Key"] for obj in response.get("Contents", [])]
    if not keys:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "PIPELINE_STATUS_NOT_FOUND",
                    "message": f"No pipeline_status record found for tenant {tenant_id}, run_id {run_id}",
                }
            },
        )
    return sorted(keys)[-1]


@router.get("/status")
async def get_pipeline_status(
    tenant_id: str = Depends(validate_tenant_header),
    run_id: str = Query(None, description="Specific run_id to look up; defaults to the most recent run"),
):
    """Return the overall SUCCESS/FAILED status of the latest (or a specific) pipeline run."""
    if not settings.S3_BUCKET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": {"code": "S3_NOT_CONFIGURED", "message": "S3_BUCKET is not configured"}},
        )

    s3 = boto3.client("s3", region_name=settings.AWS_REGION)
    try:
        effective_run_id = run_id or _latest_run_id(s3, tenant_id)
        status_key = _latest_status_key(s3, tenant_id, effective_run_id)
        obj = s3.get_object(Bucket=settings.S3_BUCKET, Key=status_key)
        record = json.loads(obj["Body"].read())
    except HTTPException:
        raise
    except (BotoCoreError, ClientError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"error": {"code": "S3_READ_FAILURE", "message": str(exc)}},
        )

    return {
        "tenant_id": record.get("tenant_id", tenant_id),
        "run_id": record.get("run_id", effective_run_id),
        "status": record.get("overall_status"),
    }
