from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models_db import IncidentDB, IncidentPayloadDB


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _upsert_payload(
    db: Session,
    incident_id: str,
    *,
    failure_payload: dict[str, Any] | None = None,
    agent_result_payload: dict[str, Any] | None = None,
) -> IncidentPayloadDB:
    now = _now_utc()
    row = db.get(IncidentPayloadDB, incident_id)
    if row is None:
        row = IncidentPayloadDB(
            incident_id=incident_id,
            failure_payload=failure_payload or {},
            agent_result_payload=agent_result_payload or {},
            created_at=now,
            updated_at=now,
        )
        db.add(row)
        return row

    if failure_payload is not None:
        row.failure_payload = failure_payload
    if agent_result_payload is not None:
        row.agent_result_payload = agent_result_payload
    row.updated_at = now
    return row


def get_incident(db: Session, incident_id: str) -> IncidentDB | None:
    return db.get(IncidentDB, incident_id)


def upsert_incident_with_failure(
    db: Session,
    *,
    incident_id: str,
    tenant_id: str,
    platform_id: str,
    pipeline: str,
    severity: str,
    problem: str,
    source: str,
    failure_payload: dict[str, Any],
) -> tuple[IncidentDB, bool]:
    now = _now_utc()
    row = db.get(IncidentDB, incident_id)
    created = row is None

    if row is None:
        row = IncidentDB(
            incident_id=incident_id,
            tenant_id=tenant_id,
            platform_id=platform_id,
            pipeline=pipeline,
            severity=severity,
            status="DETECTED",
            problem=problem,
            source=source,
            created_at=now,
            updated_at=now,
        )
        db.add(row)
    else:
        row.tenant_id = tenant_id
        row.platform_id = platform_id
        row.pipeline = pipeline
        row.severity = severity
        row.problem = problem
        row.source = source or row.source
        row.status = "DETECTED"
        row.updated_at = now

    _upsert_payload(
        db,
        incident_id,
        failure_payload=failure_payload,
        agent_result_payload={},
    )

    db.commit()
    db.refresh(row)
    return row, created


def list_incident_rows(
    db: Session,
    *,
    tenant_id: str | None = None,
    platform_id: str | None = None,
    status: str | None = None,
    severity: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[IncidentDB]:
    query = db.query(IncidentDB)
    if tenant_id:
        query = query.filter(IncidentDB.tenant_id == tenant_id)
    if platform_id:
        query = query.filter(IncidentDB.platform_id == platform_id)
    if status:
        query = query.filter(IncidentDB.status == status)
    if severity:
        query = query.filter(IncidentDB.severity == severity)

    return (
        query.order_by(IncidentDB.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


def payload_map_by_incident_ids(
    db: Session,
    incident_ids: list[str],
) -> dict[str, dict[str, Any]]:
    if not incident_ids:
        return {}

    rows = (
        db.query(IncidentPayloadDB)
        .filter(IncidentPayloadDB.incident_id.in_(incident_ids))
        .all()
    )
    return {row.incident_id: row.failure_payload or {} for row in rows}


def set_agent_invoked(
    db: Session,
    *,
    incident_id: str,
    invocation_payload: dict[str, Any],
) -> IncidentDB | None:
    row = db.get(IncidentDB, incident_id)
    if row is None:
        return None

    row.status = "SENDING_TO_AGENT"
    row.updated_at = _now_utc()

    payload_row = _upsert_payload(db, incident_id)
    previous = payload_row.agent_result_payload or {}
    previous["last_invocation"] = invocation_payload
    payload_row.agent_result_payload = previous
    payload_row.updated_at = _now_utc()

    db.commit()
    db.refresh(row)
    return row


def record_failed_remediation(
    db: Session,
    *,
    incident_id: str,
    result_payload: dict[str, Any],
) -> IncidentDB | None:
    row = db.get(IncidentDB, incident_id)
    if row is None:
        return None

    now = _now_utc()
    row.status = "ESCALATED"
    row.updated_at = now

    payload_row = _upsert_payload(db, incident_id)
    payload_row.agent_result_payload = result_payload
    payload_row.updated_at = now

    db.commit()
    db.refresh(row)
    return row


def record_success_pending_validation(
    db: Session,
    *,
    incident_id: str,
    result_payload: dict[str, Any],
) -> IncidentDB | None:
    row = db.get(IncidentDB, incident_id)
    if row is None:
        return None

    now = _now_utc()
    row.status = "VALIDATING"
    row.updated_at = now

    payload_row = _upsert_payload(db, incident_id)
    payload_row.agent_result_payload = result_payload
    payload_row.updated_at = now

    db.commit()
    db.refresh(row)
    return row


def delete_resolved_incident(db: Session, incident_id: str) -> bool:
    row = db.get(IncidentDB, incident_id)
    if row is None:
        return False

    payload_row = db.get(IncidentPayloadDB, incident_id)
    if payload_row is not None:
        db.delete(payload_row)
    db.delete(row)
    db.commit()
    return True
