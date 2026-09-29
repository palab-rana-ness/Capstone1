# QUICK ENDPOINT LIST

Base URL: {FASTAPI_BASE_URL}

HEALTH
GET    /health

INCIDENT FLOW
POST   /api/v1/incidents/failures
GET    /api/v1/incidents
POST   /api/v1/incidents/{incident_id}/agent/invoke
POST   /api/v1/incidents/{incident_id}/agent/result

STANDARD RESPONSE ENVELOPE
{
	"status": "success",
	"message": "...",
	"data": { ... },
	"meta": {
		"request_id": "uuid",
		"timestamp": "ISO-8601"
	}
}

CORE FLOW
1. New Relic -> POST /api/v1/incidents/failures
2. FastAPI stores incident in PostgreSQL (log fields removed) + notifies human
3. Reflex dashboard -> GET /api/v1/incidents
4. Human -> POST /api/v1/incidents/{incident_id}/agent/invoke
5. LangGraph/worker -> POST /api/v1/incidents/{incident_id}/agent/result
6. If result FAILED: update incident in PostgreSQL + notify human
7. If result SUCCEEDED and validated_resolved=true: delete incident + notify resolved

RULE: Reflex -> FastAPI only. FastAPI -> PostgreSQL/New Relic/LangGraph/Notification.
