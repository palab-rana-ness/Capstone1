"""Silver quality metrics (section 30): counts of input/valid/invalid/duplicate records."""

from typing import Any

from src.config.config import Settings
from src.utils.s3_log_writer import write_log_record


def build_quality_metrics(
    dataset: str,
    tenant_id: str,
    pipeline_id: str,
    run_id: str,
    input_record_count: int,
    valid_record_count: int,
    invalid_record_count: int,
    duplicate_record_count: int,
    null_violation_count: int,
    business_rule_violation_count: int,
    referential_integrity_failure_count: int,
    output_record_count: int,
    status: str = "SUCCESS",
) -> dict[str, Any]:
    return {
        "dataset": dataset,
        "tenant_id": tenant_id,
        "pipeline_id": pipeline_id,
        "run_id": run_id,
        "input_record_count": input_record_count,
        "valid_record_count": valid_record_count,
        "invalid_record_count": invalid_record_count,
        "duplicate_record_count": duplicate_record_count,
        "null_violation_count": null_violation_count,
        "business_rule_violation_count": business_rule_violation_count,
        "referential_integrity_failure_count": referential_integrity_failure_count,
        "output_record_count": output_record_count,
        "status": status,
    }


def write_quality_metrics(
    settings: Settings, tenant_id: str, run_id: str, dataset: str, metrics: dict[str, Any]
) -> str:
    return write_log_record(settings, "quality", tenant_id, run_id, dataset, metrics)
