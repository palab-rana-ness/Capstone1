# Project Implementation Map

## 1) What Is Live Right Now

The active backend flow is:

New Relic -> FastAPI -> PostgreSQL -> Notify Human -> Human invokes LangGraph -> agent result updates or deletes incident -> Notify Human

Kept API surface:
- GET /health
- POST /api/v1/incidents/failures
- GET /api/v1/incidents
- POST /api/v1/incidents/{incident_id}/agent/invoke
- POST /api/v1/incidents/{incident_id}/agent/result

Reference docs:
- [ARCHITECTURE_FLOW_DIAGRAM.md](ARCHITECTURE_FLOW_DIAGRAM.md)
- [QUICK_ENDPOINT_LIST.md](QUICK_ENDPOINT_LIST.md)

## 2) Read Order For New Teammates

1. [ARCHITECTURE_FLOW_DIAGRAM.md](ARCHITECTURE_FLOW_DIAGRAM.md)
2. [QUICK_ENDPOINT_LIST.md](QUICK_ENDPOINT_LIST.md)
3. [app/main.py](app/main.py)
4. [app/routers/incidents.py](app/routers/incidents.py)
5. [app/incident_workflow.py](app/incident_workflow.py)
6. [app/database/incident_repository.py](app/database/incident_repository.py)
7. [app/models_db.py](app/models_db.py)
8. [app/workflow_schemas.py](app/workflow_schemas.py)
9. [app/services/notification_service.py](app/services/notification_service.py)
10. [app/services/langgraph_service.py](app/services/langgraph_service.py)

## 3) Active Backend File Map

| File | Responsibility | Notes |
|---|---|---|
| [app/main.py](app/main.py) | FastAPI app wiring, startup, health check | Only incident router is included |
| [app/database/connection.py](app/database/connection.py) | SQLAlchemy engine/session setup from DATABASE_URL | Shared DB session dependency |
| [app/routers/incidents.py](app/routers/incidents.py) | HTTP endpoints for incident flow | No direct SQL in router |
| [app/incident_workflow.py](app/incident_workflow.py) | Business orchestration and status transitions | Strips log fields from incoming failure payload |
| [app/database/incident_repository.py](app/database/incident_repository.py) | All PostgreSQL CRUD for current flow | INSERT/UPDATE/DELETE centralized here |
| [app/models_db.py](app/models_db.py) | DB table models | incidents + incident_payloads |
| [app/workflow_schemas.py](app/workflow_schemas.py) | Request schemas and standardized response envelope | Flexible data fields preserved |
| [app/services/notification_service.py](app/services/notification_service.py) | Human notification abstraction | Current implementation is a stub payload |
| [app/services/langgraph_service.py](app/services/langgraph_service.py) | LangGraph invocation abstraction | Current implementation is a stub payload |

## 4) Endpoint To Code Path

1. POST /api/v1/incidents/failures
- Route: [app/routers/incidents.py](app/routers/incidents.py)
- Workflow: [ingest_failure](app/incident_workflow.py#L85)
- Repository write: [upsert_incident_with_failure](app/database/incident_repository.py#L47)
- Effect: INSERT or UPSERT incident, store payload without logs, notify human.

2. GET /api/v1/incidents
- Route: [app/routers/incidents.py](app/routers/incidents.py)
- Workflow: [list_dashboard_incidents](app/incident_workflow.py#L106)
- Repository read: [list_incident_rows](app/database/incident_repository.py#L99)
- Effect: returns dashboard incident list from PostgreSQL.

3. POST /api/v1/incidents/{incident_id}/agent/invoke
- Route: [app/routers/incidents.py](app/routers/incidents.py)
- Workflow: [mark_agent_invoked](app/incident_workflow.py#L154)
- Repository update: [set_agent_invoked](app/database/incident_repository.py#L140)
- Effect: marks incident as SENDING_TO_AGENT, records invocation payload, notifies human.

4. POST /api/v1/incidents/{incident_id}/agent/result
- Route: [app/routers/incidents.py](app/routers/incidents.py)
- Workflow: [process_agent_result](app/incident_workflow.py#L169)
- FAILED branch update: [record_failed_remediation](app/database/incident_repository.py#L166)
- SUCCESS unresolved update: [record_success_pending_validation](app/database/incident_repository.py#L189)
- SUCCESS resolved delete: [delete_resolved_incident](app/database/incident_repository.py#L212)
- Effect: update status or delete incident and notify human.

5. GET /health
- Route: [health_check](app/main.py#L28)
- Effect: verifies DB connectivity with SELECT 1.

## 5) Database Tables Used By Current Flow

1. incidents
- Core fields: incident_id, tenant_id, platform_id, pipeline, severity, status, problem, source, created_at, updated_at.

2. incident_payloads
- Stores flexible JSON for failure payload and agent result payload.
- Linked by incident_id.

## 6) Flexible Schema Contract

Current request/response models intentionally keep data fields flexible:
- Failure ingest request has incident and context as generic objects.
- Agent invoke input is generic object.
- Agent result result field is generic object.
- Standardized response envelope is used by routes:
  - status
  - message
  - data
  - meta.request_id
  - meta.timestamp

See [app/workflow_schemas.py](app/workflow_schemas.py).

## 7) Legacy Or Not Currently Wired Paths

These files exist but are not in the active route surface of app/main.py:
- [app/routers/tenants.py](app/routers/tenants.py)
- [app/routers/platforms.py](app/routers/platforms.py)

These modules are from earlier flow and should be treated as legacy/reference unless reactivated:
- [app/db_incidents.py](app/db_incidents.py)
- [app/schemas.py](app/schemas.py)
- [app/store.py](app/store.py)

## 8) Team Editing Guide

If you need to change endpoint contract:
- Edit request/response models in [app/workflow_schemas.py](app/workflow_schemas.py).

If you need to change business flow rules:
- Edit [app/incident_workflow.py](app/incident_workflow.py).

If you need to change SQL/DB behavior:
- Edit [app/database/incident_repository.py](app/database/incident_repository.py).

If you need to connect real notification or LangGraph services:
- Edit [app/services/notification_service.py](app/services/notification_service.py).
- Edit [app/services/langgraph_service.py](app/services/langgraph_service.py).

## 9) Known Gotchas

1. DATABASE_URL must match actual DB name exactly, including case.
2. Current backend table column is platform_id, not platform.
3. Manual DB inserts should include required columns expected by [app/models_db.py](app/models_db.py).
4. Keep SQL out of Reflex UI; backend repository layer is the source of truth.

## 10) Suggested Onboarding Session (60-90 min)

1. Read sections 1-4 of this file.
2. Open endpoint routes and trace each one into workflow and repository.
3. Run one test call per endpoint and verify row changes in PostgreSQL.
4. Review legacy files only after understanding active path.
