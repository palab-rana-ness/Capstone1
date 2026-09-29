"""Seed the Chroma incident memory with demo historical Spark incidents.

Run with:  python -m scripts.seed_data

This populates ./data/chroma with incidents across two tenants so that
tenant isolation can be demonstrated (tenant_001 must never see
tenant_002's incidents, and vice versa).
"""
from __future__ import annotations

from app.memory.chroma import get_default_repository
from app.models.incident import Incident
from app.utils.incident_formatter import build_memory_document

SEED_INCIDENTS: list[dict] = [
    {
        "tenant_id": "tenant_001",
        "incident_id": "INC_1001",
        "adapter": "spark",
        "pipeline": "customer_daily_pipeline",
        "status": "RESOLVED",
        "failed_stage": "aggregate_customer_data",
        "failed_task": "task_17",
        "error_message": "java.lang.OutOfMemoryError: Java heap space",
        "logs": ["Stage 12 started", "ExecutorLostFailure", "Task 17 failed"],
        "details": {"executor_memory": "4g", "executor_cores": 2, "shuffle_read_mb": 8420},
        "metadata": {"environment": "production", "region": "us-east-1"},
        "root_cause": "Executor memory exhaustion during aggregation",
        "resolution": "Increase executor memory",
    },
    {
        "tenant_id": "tenant_001",
        "incident_id": "INC_1002",
        "adapter": "spark",
        "pipeline": "orders_hourly_pipeline",
        "status": "RESOLVED",
        "failed_stage": "collect_summary",
        "failed_task": "task_3",
        "error_message": "java.lang.OutOfMemoryError: GC overhead limit exceeded (driver)",
        "logs": ["Driver started", "Broadcasting large variable", "GC overhead limit exceeded"],
        "details": {"driver_memory": "2g"},
        "metadata": {"environment": "production", "region": "us-east-1"},
        "root_cause": "Driver out-of-memory from collecting too much data",
        "resolution": "Increase driver memory and avoid collect() on large datasets",
    },
    {
        "tenant_id": "tenant_001",
        "incident_id": "INC_1003",
        "adapter": "spark",
        "pipeline": "inventory_sync_pipeline",
        "status": "RESOLVED",
        "failed_stage": "shuffle_join",
        "failed_task": "task_44",
        "error_message": "org.apache.spark.shuffle.FetchFailedException",
        "logs": ["Shuffle fetch started", "FetchFailedException", "Executor lost"],
        "details": {"shuffle_partitions": 200},
        "metadata": {"environment": "staging", "region": "us-east-1"},
        "root_cause": "Shuffle fetch failure due to lost executor",
        "resolution": "Retry pipeline and increase shuffle partitions",
    },
    {
        "tenant_id": "tenant_001",
        "incident_id": "INC_1004",
        "adapter": "spark",
        "pipeline": "customer_daily_pipeline",
        "status": "RESOLVED",
        "failed_stage": "aggregate_customer_data",
        "failed_task": "task_5",
        "error_message": "Task 5 running far longer than other tasks in stage",
        "logs": ["Stage 8 started", "Task 5 still running after 40 minutes"],
        "details": {"partition_count": 32, "max_partition_size_mb": 5000},
        "metadata": {"environment": "production", "region": "us-east-1"},
        "root_cause": "Data skew causing a single long-running task",
        "resolution": "Repartition on a higher-cardinality key",
    },
    {
        "tenant_id": "tenant_002",
        "incident_id": "INC_2001",
        "adapter": "spark",
        "pipeline": "billing_pipeline",
        "status": "RESOLVED",
        "failed_stage": "read_source",
        "failed_task": "task_1",
        "error_message": "org.apache.spark.sql.AnalysisException: cannot resolve column 'amount'",
        "logs": ["Reading source table", "AnalysisException: cannot resolve column"],
        "details": {"source_schema_version": "v2"},
        "metadata": {"environment": "production", "region": "eu-west-1"},
        "root_cause": "Upstream schema change broke column mapping",
        "resolution": "Update schema mapping to match upstream source",
    },
    {
        "tenant_id": "tenant_002",
        "incident_id": "INC_2002",
        "adapter": "spark",
        "pipeline": "billing_pipeline",
        "status": "RESOLVED",
        "failed_stage": "read_source",
        "failed_task": "task_1",
        "error_message": "java.io.FileNotFoundException: Path does not exist: /data/billing/2026-01-01",
        "logs": ["Reading source path", "Path does not exist"],
        "details": {"expected_path": "/data/billing/2026-01-01"},
        "metadata": {"environment": "production", "region": "eu-west-1"},
        "root_cause": "Expected input file/partition was missing",
        "resolution": "Verify upstream job completed and repair input path",
    },
    {
        "tenant_id": "tenant_002",
        "incident_id": "INC_2003",
        "adapter": "spark",
        "pipeline": "billing_pipeline",
        "status": "RESOLVED",
        "failed_stage": "connect_source",
        "failed_task": "task_0",
        "error_message": "java.net.ConnectException: Connection refused (source database)",
        "logs": ["Connecting to source database", "Connection refused"],
        "details": {"source": "postgres://billing-db"},
        "metadata": {"environment": "production", "region": "eu-west-1"},
        "root_cause": "Source database connection failure",
        "resolution": "Verify source connection and credentials",
    },
    {
        "tenant_id": "tenant_002",
        "incident_id": "INC_2004",
        "adapter": "spark",
        "pipeline": "billing_pipeline",
        "status": "RESOLVED",
        "failed_stage": "write_target",
        "failed_task": "task_9",
        "error_message": "java.net.ConnectException: Connection refused (target warehouse)",
        "logs": ["Writing to target warehouse", "Connection refused"],
        "details": {"target": "snowflake://warehouse"},
        "metadata": {"environment": "production", "region": "eu-west-1"},
        "root_cause": "Target warehouse connection failure",
        "resolution": "Verify target connection and credentials",
    },
]


def seed() -> None:
    repo = get_default_repository()
    for record in SEED_INCIDENTS:
        incident = Incident(
            tenant_id=record["tenant_id"],
            incident_id=record["incident_id"],
            adapter=record["adapter"],
            pipeline=record["pipeline"],
            status=record["status"],
            failed_stage=record["failed_stage"],
            failed_task=record["failed_task"],
            error_message=record["error_message"],
            logs=record["logs"],
            details=record["details"],
            metadata=record["metadata"],
        )
        document = build_memory_document(incident)
        repo.add_incident(
            incident=incident,
            document_text=document,
            status="resolved",
            extra_metadata={
                "root_cause": record["root_cause"],
                "resolution": record["resolution"],
            },
        )
        print(f"Seeded {incident.tenant_id}/{incident.incident_id}")


if __name__ == "__main__":
    seed()
