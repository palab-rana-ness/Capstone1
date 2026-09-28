# Sentinel incident workspace

The existing Dashboard, Incidents, Incident Details, and Configuration routes retain their graphite-and-amber interface. Reflex presents authorized FastAPI responses and human controls; it does not implement diagnosis, remediation policy, execution, authorization, or recovery decisions.

## Runtime settings

Supported environment variable names:

- `FASTAPI_BASE_URL`
- `FASTAPI_BEARER_TOKEN`
- `FASTAPI_TIMEOUT`
- `SENTINEL_CURRENT_USER`
- `SENTINEL_POLL_INTERVAL`
- `SENTINEL_POLL_MAX_ATTEMPTS`
- `APP_ENV`
- `REFLEX_ENV_MODE`
- `OPS_PROVIDER`
- `OPS_DEMO_SCENARIO`

The base URL is validated on each request. Transport redirects are disabled. Optional bearer authorization stays server-side; response bodies and transport exception details are not used as user-facing error messages. The current operator must be configured before analysis can be submitted. No identity is invented by the UI.

## Public endpoint inventory

| Method | Endpoint |
| --- | --- |
| GET | `/api/v1/incidents` |
| GET | `/api/v1/incidents/{id}` |
| GET | `/api/v1/incidents/{id}/timeline` |
| GET | `/api/v1/incidents/{id}/logs` |
| POST | `/api/v1/incidents/{id}/logs/refresh` |
| POST | `/api/v1/incidents/{id}/analyze` |
| GET | `/api/v1/incidents/{id}/diagnosis` |
| GET | `/api/v1/incidents/{id}/history` |
| GET | `/api/v1/incidents/{id}/remediation` |
| POST | `/api/v1/incidents/{id}/approve` |
| POST | `/api/v1/incidents/{id}/reject` |
| POST | `/api/v1/incidents/{id}/retry` |
| GET | `/api/v1/incidents/{id}/execution` |
| GET | `/api/v1/incidents/{id}/validation` |
| GET | `/api/v1/tenants` |
| GET | `/api/v1/tenants/{tenant_id}/incidents` |
| GET, PUT | `/api/v1/tenants/{tenant_id}/config` |
| GET | `/api/v1/platforms` |
| GET | `/api/v1/platforms/{platform}/config` |

Analysis sends exactly `requested_by` and `reason`. Action writes carry an idempotency key; a timeout never triggers an automatic resubmission. Refresh Logs sends one POST. Configuration saves require a definitive saved response and an advanced revision. API mode never uses legacy operation URLs.

## Scope and response rules

Catalogs supply the authorized tenant and platform options. After tenant selection, incident lists use the tenant-specific endpoint, with the selected platform included as query context. Search, filtering, and sorting operate only on already-authorized results. The UI never fetches a cross-tenant collection and filters it into a tenant workspace.

Switching workspace clears incident lists, dashboard data, details, logs, pending confirmations, polling generation, and configuration drafts before a new scoped load. Late detail responses are checked against generation, route, incident, and scope. Supplied tenant, platform, and incident echoes must match. Malformed responses fail closed rather than granting actions or showing partial incident results.

Direct JSON responses and supported data envelopes are normalized to typed values. Optional sections can be unavailable without fabricating a diagnosis or recommendation. Timeline timestamps are parsed before sorting; unparseable or absent timestamps retain their relative order after dated entries. Only explicitly returned action capabilities enable controls.

## Lifecycle

A human selects Send to Agent, optionally adding a reason. The control locks immediately and displays Sending to Agent. An accepted response is asynchronous, not proof that analysis succeeded. One guarded, bounded polling task reconciles incident status, execution, and validation. Poll settings are bounded and validated.

Polling stops at backend handoffs such as diagnosed, remediation proposed, awaiting approval, resolved, rejected, or escalated; it also stops on authorization/not-found failures, route/scope changes, or its attempt limit. Execution and validation remain independently visible. Diagnosis, similar history, remediation, and audit are refreshed around status changes. Failed actions retain the audit already received.

The backend status is retained. A resolved status without explicit recovery confirmation is displayed as Recovery unconfirmed, not Resolved. Failed validation can preserve an explicit escalated outcome. Rejected and escalated outcomes are never converted into successful recovery. HTTP success alone is not workflow success.

HTTP errors distinguish invalid request, unauthorized, not found, conflict, validation failure, unavailable service, timeout, and malformed response. Conflict means another action may already be running; the operator should reconcile rather than repeat a write blindly.

## Local development

The existing synthetic development provider remains isolated behind the service boundary and is replaceable. It is disabled outside development and is not selected when the FastAPI integration is configured. Synthetic approval, rejection, successful retry, and failed-retry scenarios remain available. Existing local fixture persistence is for synthetic development data only.

PostgreSQL, New Relic, and LangGraph are backend-only. Reflex does not connect to PostgreSQL or New Relic, invoke LangGraph, or introduce application authentication or production database access.

## Focused checks

The unittest modules cover transport status mappings, endpoint methods and bodies, scoped catalogs/configuration, response normalization, timeline ordering, explicit recovery confirmation, duplicate-action and polling guards, stale-scope invalidation, synthetic remediation behavior, and construction of all four existing page components. Run these checks in the configured Reflex Python environment before release.
