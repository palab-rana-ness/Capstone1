from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.incident_workflow import (
    get_incident_row,
    ingest_failure,
    list_dashboard_incidents,
    mark_agent_invoked,
    process_agent_result,
)
from app.services.langgraph_service import langgraph_service
from app.services.notification_service import notification_service
from app.workflow_schemas import (
    AgentInvokeRequest,
    AgentResultRequest,
    FailureIngestRequest,
    StandardApiResponse,
    response_ok,
)

router = APIRouter(prefix="/api/v1/incidents", tags=["IncidentFlow"])


@router.post("/failures", response_model=StandardApiResponse, status_code=202)
def receive_new_relic_failure(
    body: FailureIngestRequest,
    db: Session = Depends(get_db),
):
    row, created = ingest_failure(db, body)
    notification = notification_service.notify_human(
        incident_id=row.incident_id,
        title="Incident detected",
        message="A new failure was stored and requires human review.",
        context={
            "status": row.status,
            "severity": row.severity,
            "source": row.source,
        },
    )
    return response_ok(
        "Failure received from New Relic and stored in PostgreSQL.",
        {
            "incident_id": row.incident_id,
            "created": created,
            "status": row.status,
            "notification": notification,
        },
    )


@router.get("", response_model=StandardApiResponse)
def get_dashboard_incidents(
    tenant_id: str | None = None,
    platform_id: str | None = None,
    status: str | None = None,
    severity: str | None = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    items = list_dashboard_incidents(
        db,
        tenant_id=tenant_id,
        platform_id=platform_id,
        status=status,
        severity=severity,
        limit=limit,
        offset=offset,
    )
    return response_ok(
        "Dashboard incidents fetched from PostgreSQL.",
        {
            "items": items,
            "count": len(items),
            "filters": {
                "tenant_id": tenant_id,
                "platform_id": platform_id,
                "status": status,
                "severity": severity,
                "limit": limit,
                "offset": offset,
            },
        },
    )


@router.post("/{incident_id}/agent/invoke", response_model=StandardApiResponse)
def invoke_langgraph_agent(
    incident_id: str,
    body: AgentInvokeRequest,
    db: Session = Depends(get_db),
):
    row = get_incident_row(db, incident_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Incident not found")

    invocation = langgraph_service.invoke(
        incident_id=incident_id,
        requested_by=body.requested_by,
        action=body.action,
        payload=body.input,
    )
    row = mark_agent_invoked(
        db,
        incident_id=incident_id,
        invocation_payload=invocation,
    )

    notification = notification_service.notify_human(
        incident_id=incident_id,
        title="LangGraph invocation started",
        message="Human-approved remediation was sent to the LangGraph agent.",
        context={
            "status": row.status,
            "requested_by": body.requested_by,
            "action": body.action,
            "invocation_id": invocation["invocation_id"],
        },
    )
    return response_ok(
        "LangGraph invocation accepted.",
        {
            "incident_id": incident_id,
            "status": row.status,
            "invocation": invocation,
            "notification": notification,
        },
    )


@router.post("/{incident_id}/agent/result", response_model=StandardApiResponse)
def record_agent_result(
    incident_id: str,
    body: AgentResultRequest,
    db: Session = Depends(get_db),
):
    try:
        result = process_agent_result(
            db,
            incident_id=incident_id,
            body=body,
        )
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error

    if result["deleted"]:
        title = "Error resolved"
        message = "Failure is corrected, validation passed, incident row was deleted from PostgreSQL, and the error is resolved."
    elif body.outcome == "FAILED":
        title = "Remediation failed"
        message = "LangGraph remediation failed. Incident was updated and remains open."
    else:
        title = "Remediation complete, validation pending"
        message = "Remediation succeeded but resolution validation is still pending."

    notification = notification_service.notify_human(
        incident_id=incident_id,
        title=title,
        message=message,
        context={
            "outcome": body.outcome,
            "validated_resolved": body.validated_resolved,
            "status": result["status"],
            "deleted": result["deleted"],
        },
    )
    return response_ok(
        "Agent result processed.",
        {
            **result,
            "notification": notification,
        },
    )
