from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from app.database import incident_repository
from app.models_db import IncidentDB
from app.workflow_schemas import AgentResultRequest, FailureIngestRequest

_ALLOWED_SEVERITIES = {"CRITICAL", "HIGH", "MEDIUM", "LOW"}
_LOG_KEYS = {"log", "logs", "log_entry", "log_entries", "raw_logs"}


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _as_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text or default


def _normalize_severity(value: Any) -> str:
    candidate = _as_text(value, "MEDIUM").upper()
    return candidate if candidate in _ALLOWED_SEVERITIES else "MEDIUM"


def _strip_logs(value: Any) -> Any:
    if isinstance(value, Mapping):
        cleaned: dict[str, Any] = {}
        for key, item in value.items():
            key_text = str(key)
            if key_text.lower() in _LOG_KEYS:
                continue
            cleaned[key_text] = _strip_logs(item)
        return cleaned
    if isinstance(value, list):
        return [_strip_logs(item) for item in value]
    return value


def _incident_id(payload: dict[str, Any]) -> str:
    existing = _as_text(payload.get("incident_id") or payload.get("id"))
    if existing:
        return existing
    return f"INC-{uuid4().hex[:10].upper()}"


def _tenant_id(payload: dict[str, Any], context: dict[str, Any]) -> str:
    return _as_text(
        payload.get("tenant_id") or payload.get("tenant") or context.get("tenant_id"),
        "UNKNOWN_TENANT",
    )


def _platform_id(payload: dict[str, Any], context: dict[str, Any]) -> str:
    return _as_text(
        payload.get("platform_id")
        or payload.get("platform")
        or context.get("platform_id"),
        "UNKNOWN_PLATFORM",
    )


def _problem(payload: dict[str, Any], context: dict[str, Any]) -> str:
    return _as_text(
        payload.get("problem")
        or payload.get("summary")
        or context.get("problem")
        or context.get("summary"),
        "Failure detected from New Relic",
    )


def _pipeline(payload: dict[str, Any], context: dict[str, Any]) -> str:
    return _as_text(payload.get("pipeline") or payload.get("pipeline_name") or context.get("pipeline"))


def ingest_failure(db: Session, body: FailureIngestRequest) -> tuple[IncidentDB, bool]:
    payload = body.incident if isinstance(body.incident, dict) else {}
    context = body.context if isinstance(body.context, dict) else {}
    incident_id = _incident_id(payload)
    clean_payload = _strip_logs(payload)
    row, created = incident_repository.upsert_incident_with_failure(
        db,
        incident_id=incident_id,
        tenant_id=_tenant_id(payload, context),
        platform_id=_platform_id(payload, context),
        pipeline=_pipeline(payload, context),
        severity=_normalize_severity(
            payload.get("severity") or context.get("severity")
        ),
        problem=_problem(payload, context),
        source=_as_text(body.source, "NEW_RELIC"),
        failure_payload=clean_payload,
    )
    return row, created


def list_dashboard_incidents(
    db: Session,
    *,
    tenant_id: str | None = None,
    platform_id: str | None = None,
    status: str | None = None,
    severity: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict[str, Any]]:
    rows = incident_repository.list_incident_rows(
        db,
        tenant_id=tenant_id,
        platform_id=platform_id,
        status=status,
        severity=severity,
        limit=limit,
        offset=offset,
    )

    ids = [row.incident_id for row in rows]
    payload_by_id = incident_repository.payload_map_by_incident_ids(db, ids)

    result: list[dict[str, Any]] = []
    for row in rows:
        result.append(
            {
                "incident_id": row.incident_id,
                "tenant_id": row.tenant_id,
                "platform_id": row.platform_id,
                "pipeline": row.pipeline,
                "severity": row.severity,
                "status": row.status,
                "problem": row.problem,
                "source": row.source,
                "created_at": row.created_at.isoformat(),
                "updated_at": row.updated_at.isoformat(),
                "details": payload_by_id.get(row.incident_id, {}),
            }
        )
    return result


def get_incident_row(db: Session, incident_id: str) -> IncidentDB | None:
    return incident_repository.get_incident(db, incident_id)


def mark_agent_invoked(
    db: Session,
    *,
    incident_id: str,
    invocation_payload: dict[str, Any],
) -> IncidentDB:
    row = incident_repository.set_agent_invoked(
        db,
        incident_id=incident_id,
        invocation_payload=invocation_payload,
    )
    if row is None:
        raise ValueError("Incident not found")
    return row


def process_agent_result(
    db: Session,
    *,
    incident_id: str,
    body: AgentResultRequest,
) -> dict[str, Any]:
    row = incident_repository.get_incident(db, incident_id)
    if row is None:
        raise ValueError("Incident not found")

    now = _now_utc()

    result_payload = {
        "outcome": body.outcome,
        "validated_resolved": body.validated_resolved,
        "result": body.result,
        "error": body.error,
        "updated_at": now.isoformat(),
    }

    if body.outcome == "FAILED":
        updated = incident_repository.record_failed_remediation(
            db,
            incident_id=incident_id,
            result_payload=result_payload,
        )
        if updated is None:
            raise ValueError("Incident not found")
        return {
            "resolved": False,
            "deleted": False,
            "incident_id": updated.incident_id,
            "status": updated.status,
        }

    if body.validated_resolved:
        deleted = incident_repository.delete_resolved_incident(db, incident_id)
        if not deleted:
            raise ValueError("Incident not found")
        return {
            "resolved": True,
            "deleted": True,
            "incident_id": incident_id,
            "status": "RESOLVED",
        }

    updated = incident_repository.record_success_pending_validation(
        db,
        incident_id=incident_id,
        result_payload=result_payload,
    )
    if updated is None:
        raise ValueError("Incident not found")
    return {
        "resolved": False,
        "deleted": False,
        "incident_id": updated.incident_id,
        "status": updated.status,
    }
