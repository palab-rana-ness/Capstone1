# Teammate Onboarding Guide

## Purpose

This guide helps new teammates become productive in this project quickly.

Use this together with:
- [PROJECT_IMPLEMENTATION_MAP.md](PROJECT_IMPLEMENTATION_MAP.md)
- [ARCHITECTURE_FLOW_DIAGRAM.md](ARCHITECTURE_FLOW_DIAGRAM.md)
- [QUICK_ENDPOINT_LIST.md](QUICK_ENDPOINT_LIST.md)

## Day 1 Plan (45-60 minutes)

1. Understand what is currently implemented.
2. Run backend and verify health.
3. Run core incident flow endpoints.
4. Verify PostgreSQL rows in pgAdmin.
5. Identify the right file to edit for your task.

## Current Implemented Scope

Active flow:

New Relic -> FastAPI -> PostgreSQL -> Notify Human -> Human invokes LangGraph -> Agent result updates/deletes incident -> Notify Human

Current public backend endpoints:
- GET /health
- POST /api/v1/incidents/failures
- GET /api/v1/incidents
- POST /api/v1/incidents/{incident_id}/agent/invoke
- POST /api/v1/incidents/{incident_id}/agent/result

## Local Setup

1. Python environment
- Use the project Python environment selected in VS Code.

2. Install dependencies
- pip install -r requirements.txt

3. Environment file
- Ensure .env has:
  - DATABASE_URL (must match DB name case exactly)
  - FASTAPI_BASE_URL (if UI calls backend)
  - FASTAPI_TIMEOUT

4. PostgreSQL
- Confirm database exists and is reachable from DATABASE_URL.
- For this workspace, DB name case matters (for example Incident_management vs incident_management).

## Run Services

1. Start FastAPI backend on port 8001
- uvicorn app.main:app --reload --port 8001

2. Keep Reflex on a different port (default 8000)
- Do not run uvicorn on 8000 when Reflex is running.

## Quick Verification Steps

1. Health
- GET http://localhost:8001/health
- Expect database connected status.

2. Ingest failure (creates or updates incident)
- POST http://localhost:8001/api/v1/incidents/failures
- Example body:
{
  "source": "NEW_RELIC",
  "incident": {
    "incident_id": "INC-ONBOARD-001",
    "tenant_id": "TENANT-A",
    "platform_id": "SYNAPSE",
    "pipeline": "Orders Pipeline",
    "severity": "HIGH",
    "problem": "Pipeline failed"
  },
  "context": {}
}

3. Fetch dashboard incidents
- GET http://localhost:8001/api/v1/incidents
- Confirm new row appears.

4. Human invokes agent
- POST http://localhost:8001/api/v1/incidents/INC-ONBOARD-001/agent/invoke
- Example body:
{
  "requested_by": "teammate",
  "action": "REMEDIATE",
  "input": {}
}

5. Agent result failed (updates status)
- POST http://localhost:8001/api/v1/incidents/INC-ONBOARD-001/agent/result
- Example body:
{
  "outcome": "FAILED",
  "validated_resolved": false,
  "result": {},
  "error": "retry failed"
}

6. Agent result success + validated resolved (deletes row)
- POST http://localhost:8001/api/v1/incidents/INC-ONBOARD-001/agent/result
- Example body:
{
  "outcome": "SUCCEEDED",
  "validated_resolved": true,
  "result": {},
  "error": ""
}

7. Verify in pgAdmin
- Check incidents table and incident_payloads table.
- Resolved validated incident should be deleted.

## Where To Edit Code

1. API routes
- [app/routers/incidents.py](app/routers/incidents.py)

2. Workflow and business rules
- [app/incident_workflow.py](app/incident_workflow.py)

3. PostgreSQL operations (INSERT/UPDATE/DELETE)
- [app/database/incident_repository.py](app/database/incident_repository.py)

4. DB models
- [app/models_db.py](app/models_db.py)

5. Request/response schemas and standard envelope
- [app/workflow_schemas.py](app/workflow_schemas.py)

6. External integration adapters
- [app/services/notification_service.py](app/services/notification_service.py)
- [app/services/langgraph_service.py](app/services/langgraph_service.py)

## Important Team Rules

1. Keep SQL and DB access in backend repository layer only.
2. Do not put SQL inside Reflex UI.
3. Keep response envelope standard: status, message, data, meta.
4. Preserve human-triggered agent invocation (no auto-trigger from backend).
5. Keep endpoint surface minimal unless team agrees on expansion.

## Legacy Notes

These files exist but are not in the currently wired backend route surface:
- [app/routers/tenants.py](app/routers/tenants.py)
- [app/routers/platforms.py](app/routers/platforms.py)
- [app/db_incidents.py](app/db_incidents.py)
- [app/schemas.py](app/schemas.py)
- [app/store.py](app/store.py)

Treat them as legacy/reference unless explicitly reactivated.

## Common Issues and Fixes

1. Health endpoint says DB disconnected
- Check DATABASE_URL and DB server availability.

2. API runs but pgAdmin does not show expected rows
- Refresh tables manually in pgAdmin.
- Confirm app is connected to same database name and case.

3. Port conflicts
- Reflex and uvicorn should not share port 8000.
- Keep uvicorn on 8001 while Reflex uses 8000.

4. Manual SQL insert mismatch
- Current table uses platform_id, not platform.
- Ensure required columns match model in app/models_db.py.
