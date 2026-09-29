from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models_db import IncidentDB
from app.schemas import Incident, IncidentCreate


def humanize(value: str) -> str:
    words = value.replace("_", " ").replace("-", " ").split()
    return " ".join(word.capitalize() for word in words) if words else value


def to_schema(row: IncidentDB) -> Incident:
    return Incident(
        incident_id=row.incident_id,
        tenant_id=row.tenant_id,
        tenant_name=humanize(row.tenant_id),
        platform_id=row.platform_id,
        platform_name=humanize(row.platform_id),
        pipeline=row.pipeline,
        severity=row.severity,
        status=row.status,
        problem=row.problem,
        created_at=row.created_at,
        updated_at=row.updated_at,
        source=row.source,
    )


def list_incidents(
    db: Session,
    *,
    tenant_id: str | None = None,
    platform_id: str | None = None,
    status: str | None = None,
    severity: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Incident]:
    query = db.query(IncidentDB)
    if tenant_id:
        query = query.filter(IncidentDB.tenant_id == tenant_id)
    if platform_id:
        query = query.filter(IncidentDB.platform_id == platform_id)
    if status:
        query = query.filter(IncidentDB.status == status)
    if severity:
        query = query.filter(IncidentDB.severity == severity)
    rows = (
        query.order_by(IncidentDB.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return [to_schema(row) for row in rows]


def get_incident_row(db: Session, incident_id: str) -> IncidentDB | None:
    return db.get(IncidentDB, incident_id)


def next_incident_id(db: Session) -> str:
    return f"INC-{db.query(IncidentDB).count() + 1:03d}"


def create_incident(db: Session, body: IncidentCreate) -> IncidentDB:
    now = datetime.now(timezone.utc)
    row = IncidentDB(
        incident_id=next_incident_id(db),
        tenant_id=body.tenant_id,
        platform_id=body.platform,
        pipeline=body.pipeline,
        severity=body.severity,
        status="DETECTED",
        problem=body.problem,
        source=body.source,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def set_status(db: Session, row: IncidentDB, status: str) -> IncidentDB:
    row.status = status
    row.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return row
