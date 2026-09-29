from datetime import datetime, timedelta, timezone

from sqlalchemy import inspect, text
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
    _ensure_incidents_schema_compatibility(engine)


def _ensure_incidents_schema_compatibility(engine) -> None:
    inspector = inspect(engine)
    if "incidents" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("incidents")}
    required_columns: dict[str, str] = {
        "tenant_id": "VARCHAR",
        "platform_id": "VARCHAR",
        "pipeline": "VARCHAR",
        "severity": "VARCHAR",
        "status": "VARCHAR",
        "problem": "VARCHAR",
        "source": "VARCHAR",
        "created_at": "TIMESTAMP",
        "updated_at": "TIMESTAMP",
    }
    defaults: dict[str, str] = {
        "tenant_id": "'UNKNOWN_TENANT'",
        "platform_id": "'UNKNOWN_PLATFORM'",
        "pipeline": "''",
        "severity": "'MEDIUM'",
        "status": "'DETECTED'",
        "problem": "''",
        "source": "'NEW_RELIC'",
        "created_at": "CURRENT_TIMESTAMP",
        "updated_at": "CURRENT_TIMESTAMP",
    }
    legacy_sources: dict[str, str] = {
        "platform_id": "platform",
    }
    if all(column in columns for column in required_columns):
        return

    missing = [
        column for column in required_columns if column not in columns
    ]
    not_null_columns = set(required_columns)
    postgresql_timestamp_columns = {"created_at", "updated_at"}

    dialect = engine.dialect.name
    with engine.begin() as connection:
        for column in missing:
            column_type = required_columns[column]
            if dialect == "postgresql" and column in postgresql_timestamp_columns:
                column_type = "TIMESTAMP WITH TIME ZONE"
            connection.execute(
                text(
                    f"ALTER TABLE incidents ADD COLUMN {column} {column_type}"
                )
            )

        for column in required_columns:
            if column in legacy_sources and legacy_sources[column] in columns:
                source_column = legacy_sources[column]
                connection.execute(
                    text(
                        f"UPDATE incidents SET {column} = {source_column} WHERE {column} IS NULL"
                    )
                )

            connection.execute(
                text(
                    f"UPDATE incidents SET {column} = {defaults[column]} WHERE {column} IS NULL"
                )
            )

        if dialect == "postgresql":
            for column in not_null_columns:
                connection.execute(
                    text(
                        f"ALTER TABLE incidents ALTER COLUMN {column} SET NOT NULL"
                    )
                )

        if "tenant_id" in required_columns:
            connection.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_incidents_tenant_id ON incidents (tenant_id)"
                )
            )
        if "platform_id" in required_columns:
            connection.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_incidents_platform_id ON incidents (platform_id)"
                )
            )


def seed_if_empty(db: Session) -> None:
    if db.query(IncidentDB).count() > 0:
        return
    for data in SEED_INCIDENTS:
        db.add(IncidentDB(updated_at=data["created_at"], **data))
    db.commit()
