# TEAMMATE API + INTEGRATION SPEC

## Architecture
Reflex -> FastAPI -> PostgreSQL / New Relic / LangGraph / Platform Adapter.

Frontend never directly calls DB, New Relic or LangGraph.

## Endpoints

### Incidents
GET /api/v1/incidents
- Dashboard list.
- Query: tenant_id (if permitted), status, severity, platform, limit, offset.

GET /api/v1/incidents/{incident_id}
- Authoritative incident details + workflow status.

POST /api/v1/incidents
Request:
{
  "tenant_id": "TENANT-A",
  "pipeline": "Orders Pipeline",
  "platform": "SYNAPSE",
  "severity": "HIGH",
  "problem": "Pipeline execution failed",
  "source": "NEW_RELIC"
}

### Logs / New Relic
GET /api/v1/incidents/{incident_id}/logs
Response:
{
  "incident_id": "INC-001",
  "items": [
    {
      "log_id": "LOG-1001",
      "timestamp": "2026-09-24T10:29:51Z",
      "level": "ERROR",
      "source": "pipeline",
      "message": "Connection timeout",
      "fields": {}
    }
  ]
}

POST /api/v1/incidents/{incident_id}/logs/refresh
Backend: authorize -> query New Relic -> normalize -> persist -> return result.
Never expose New Relic credentials to Reflex.

### Agent
POST /api/v1/incidents/{incident_id}/analyze
Request:
{
  "requested_by": "user-123",
  "reason": "Please investigate this failure"
}
Backend: auth/tenant check -> fetch authoritative evidence -> LangGraph -> persist result.
May return an asynchronous/in-progress status.

GET /api/v1/incidents/{incident_id}/diagnosis
Returns root_cause, confidence, evidence, severity.

GET /api/v1/incidents/{incident_id}/history
Returns similar historical incidents.

### Remediation
GET /api/v1/incidents/{incident_id}/remediation
Example:
{
  "incident_id": "INC-001",
  "action": "RETRY",
  "reason": "Transient dependency timeout",
  "risk": "LOW",
  "approval_required": true,
  "allowed": true
}

POST /api/v1/incidents/{incident_id}/approve
Request: {"approved_by":"user-123","comment":"Approved after reviewing logs"}

POST /api/v1/incidents/{incident_id}/reject
Request: {"rejected_by":"user-123","comment":"Need further investigation"}

POST /api/v1/incidents/{incident_id}/retry
Request: {"requested_by":"user-123","reason":"Approved retry"}
Backend re-checks authorization, tenant, state, policy and duplicate execution, then calls adapter.retry().

### Execution / validation
GET /api/v1/incidents/{incident_id}/execution
Example:
{
  "incident_id":"INC-001",
  "status":"RUNNING",
  "action":"RETRY",
  "started_at":"...",
  "completed_at":null,
  "message":"Retry in progress"
}

GET /api/v1/incidents/{incident_id}/validation
Example:
{
  "incident_id":"INC-001",
  "status":"SUCCESS",
  "recovery_confirmed":true,
  "pipeline_status":"SUCCESS",
  "checked_at":"..."
}

Only backend validation should move incident to RESOLVED.

### Audit
GET /api/v1/incidents/{incident_id}/timeline

Example:
{
  "incident_id":"INC-001",
  "events":[
    {"event_id":"EV-1","event":"INCIDENT_CREATED","timestamp":"...","actor":"system","details":{}}
  ]
}

### Tenant / platform
GET /api/v1/tenants
GET /api/v1/tenants/{tenant_id}/incidents
GET /api/v1/tenants/{tenant_id}/config
PUT /api/v1/tenants/{tenant_id}/config
GET /api/v1/platforms
GET /api/v1/platforms/{platform}/config

## Recommended normalized agent input
{
  "incident_id":"INC-001",
  "tenant_id":"TENANT-A",
  "pipeline":"Orders Pipeline",
  "platform":"SYNAPSE",
  "severity":"HIGH",
  "problem":"Pipeline execution failed",
  "evidence":{
    "pipeline_status":"FAILED",
    "logs":[],
    "recent_failures":[],
    "metrics":{}
  }
}

## Recommended LangGraph result
{
  "incident_id":"INC-001",
  "diagnosis":{
    "root_cause":"Dependency database timeout",
    "confidence":0.92,
    "evidence":["LOG-1001"]
  },
  "historical_matches":["INC-018"],
  "remediation":{
    "action":"RETRY",
    "risk":"LOW",
    "reason":"Transient dependency timeout"
  }
}

## Minimum DB tables
incidents
incident_logs
agent_runs
remediation_executions
validation_results
audit_events

## Suggested incident fields
incident_id, tenant_id, pipeline, platform, severity, status, problem, created_at, updated_at, source.

## Suggested log fields
log_id, incident_id, timestamp, level, source, message, structured_fields.

## Standard HTTP behavior
200 success
201 created
202 accepted/asynchronous
400 invalid request
401 unauthenticated
403 unauthorized/tenant denied
404 not found
409 state/action conflict
422 validation error
500 backend error
502/503 upstream integration unavailable

## End-to-end call chains

1. Incident registration:
Monitoring/New Relic -> POST /incidents -> PostgreSQL
Reflex -> GET /incidents

2. Open incident:
Reflex -> GET /incidents/{id}
Reflex -> GET /incidents/{id}/logs
Reflex -> GET /incidents/{id}/timeline

3. Human sends to agent:
Reflex -> POST /incidents/{id}/analyze
FastAPI -> LangGraph
LangGraph -> FastAPI
FastAPI -> PostgreSQL
Reflex -> GET /incidents/{id} (poll)

4. Agent result:
Reflex -> GET /diagnosis
Reflex -> GET /history
Reflex -> GET /remediation

5. Human approval:
Reflex -> POST /approve OR /reject
FastAPI -> policy check -> execute if approved

6. Retry:
FastAPI -> adapter.retry()
Reflex -> GET /execution

7. Validation:
FastAPI/adapter -> validate()
Reflex -> GET /validation
FastAPI persists RESOLVED or ESCALATED.

## Team split
Backend/DB:
- PostgreSQL schema
- incident CRUD
- logs/audit persistence
- tenant filtering

New Relic:
- log collection/query
- normalization
- incident-log mapping
- /logs/refresh
- upstream error handling

Agent:
- LangGraph workflow
- /analyze
- diagnosis/history/remediation
- execution/validation integration
- workflow persistence

Frontend:
- Reflex API client
- dashboard/detail/logs
- analyze/approval/retry
- polling
- audit
- error/loading states

## Freeze before parallel development
Agree exact JSON field names, status enums, IDs, UTC ISO-8601 timestamps, authentication, tenant authorization, async behavior, error schema, pagination and terminal polling states.
