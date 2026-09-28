from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models_db import Base, IncidentDB

_NOW = datetime.now(timezone.utc)

SEED_INCIDENTS = [
    dict(
        incident_id="INC-001",
        tenant_id="TENANT-A",
        platform_id="SYNAPSE",
        pipeline="Orders Pipeline",
        severity="HIGH",
        status="AWAITING_APPROVAL",
        problem="Pipeline execution failed",
        source="NEW_RELIC",
        created_at=_NOW - timedelta(hours=1),
    ),
    dict(
        incident_id="INC-4004",
        tenant_id="TENANT-B",
        platform_id="DATABRICKS",
        pipeline="Inventory Sync",
        severity="CRITICAL",
        status="DETECTED",
        problem="Job cluster failed to start",
        source="NEW_RELIC",
        created_at=_NOW - timedelta(hours=2),
    ),
    dict(
        incident_id="INC-1635",
        tenant_id="TENANT-A",
        platform_id="SYNAPSE",
        pipeline="Customer ETL",
        severity="MEDIUM",
        status="DIAGNOSED",
        problem="Slowly changing dimension merge failed",
        source="NEW_RELIC",
        created_at=_NOW - timedelta(hours=5),
    ),
    dict(
        incident_id="INC-9948",
        tenant_id="TENANT-C",
        platform_id="AIRFLOW",
        pipeline="Billing Extract",
        severity="LOW",
        status="RESOLVED",
        problem="Upstream file arrived late",
        source="NEW_RELIC",
        created_at=_NOW - timedelta(days=1),
    ),
    dict(
        incident_id="INC-139",
        tenant_id="TENANT-B",
        platform_id="DATABRICKS",
        pipeline="Fraud Detection",
        severity="HIGH",
        status="REMEDIATING",
        problem="Feature store write timeout",
        source="NEW_RELIC",
        created_at=_NOW - timedelta(hours=8),
    ),
    dict(
        incident_id="INC-2077",
        tenant_id="TENANT-A",
        platform_id="SYNAPSE",
        pipeline="Payments Pipeline",
        severity="CRITICAL",
        status="ESCALATED",
        problem="Downstream connection timeout",
        source="NEW_RELIC",
        created_at=_NOW - timedelta(hours=3),
    ),
    dict(
        incident_id="INC-3012",
        tenant_id="TENANT-C",
        platform_id="AIRFLOW",
        pipeline="Shipment Tracking",
        severity="MEDIUM",
        status="INVESTIGATING",
        problem="DAG task retries exhausted",
        source="NEW_RELIC",
        created_at=_NOW - timedelta(hours=6),
    ),
    dict(
        incident_id="INC-4510",
        tenant_id="TENANT-B",
        platform_id="DATABRICKS",
        pipeline="Marketing Sync",
        severity="LOW",
        status="REJECTED",
        problem="Duplicate rows detected in target table",
        source="NEW_RELIC",
        created_at=_NOW - timedelta(days=2),
    ),
]


def init_db(engine) -> None:
    Base.metadata.create_all(bind=engine)


def seed_if_empty(db: Session) -> None:
    if db.query(IncidentDB).count() > 0:
        return
    for data in SEED_INCIDENTS:
        db.add(IncidentDB(updated_at=data["created_at"], **data))
    db.commit()
