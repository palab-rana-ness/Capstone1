from datetime import datetime, timedelta, timezone

from app.schemas import (
    AuditEvent,
    Diagnosis,
    ExecutionStatus,
    HistoricalMatch,
    LogEntry,
    Platform,
    PlatformConfig,
    Remediation,
    Tenant,
    TenantConfig,
    ValidationStatus,
)

_NOW = datetime(2026, 9, 24, 10, 29, 51, tzinfo=timezone.utc)

# Incident records now live in Postgres - see app/models_db.py and app/db_incidents.py.

logs: dict[str, list[LogEntry]] = {
    "INC-001": [
        LogEntry(
            log_id="LOG-1001",
            timestamp=_NOW,
            level="ERROR",
            source="pipeline",
            message="Connection timeout",
            fields={},
        )
    ]
}

diagnoses: dict[str, Diagnosis] = {
    "INC-001": Diagnosis(
        incident_id="INC-001",
        root_cause="Dependency database timeout",
        confidence=0.92,
        evidence=["LOG-1001"],
        severity="HIGH",
    )
}

history: dict[str, list[HistoricalMatch]] = {
    "INC-001": [
        HistoricalMatch(
            incident_id="INC-018",
            similarity=0.92,
            summary="Matching timeout signature; recovered after a single retry",
        )
    ]
}

remediations: dict[str, Remediation] = {
    "INC-001": Remediation(
        incident_id="INC-001",
        action="RETRY",
        reason="Transient dependency timeout",
        risk="LOW",
        approval_required=True,
        allowed=True,
    )
}

executions: dict[str, ExecutionStatus] = {
    "INC-001": ExecutionStatus(
        incident_id="INC-001",
        status="RUNNING",
        action="RETRY",
        started_at=_NOW,
        completed_at=None,
        message="Retry in progress",
    )
}

validations: dict[str, ValidationStatus] = {
    "INC-001": ValidationStatus(
        incident_id="INC-001",
        status="SUCCESS",
        recovery_confirmed=True,
        pipeline_status="SUCCESS",
        checked_at=_NOW,
    )
}

timelines: dict[str, list[AuditEvent]] = {
    "INC-001": [
        AuditEvent(
            event_id="EV-1",
            event="INCIDENT_CREATED",
            timestamp=_NOW,
            actor="system",
            details={},
        )
    ]
}

tenants: dict[str, Tenant] = {
    "TENANT-A": Tenant(tenant_id="TENANT-A", name="Tenant A"),
    "TENANT-B": Tenant(tenant_id="TENANT-B", name="Tenant B"),
    "TENANT-C": Tenant(tenant_id="TENANT-C", name="Tenant C"),
}

tenant_configs: dict[str, TenantConfig] = {
    "TENANT-A": TenantConfig(
        tenant_id="TENANT-A",
        monitoring_enabled=True,
        remediation_policy="AUTO_LOW_RISK",
        allowed_actions=["Retry"],
    ),
}

platforms: dict[str, Platform] = {
    "SYNAPSE": Platform(platform_id="SYNAPSE", name="Azure Synapse"),
    "DATABRICKS": Platform(platform_id="DATABRICKS", name="Databricks"),
    "AIRFLOW": Platform(platform_id="AIRFLOW", name="Airflow"),
}

platform_configs: dict[str, PlatformConfig] = {
    "SYNAPSE": PlatformConfig(platform_id="SYNAPSE", config={}),
}
