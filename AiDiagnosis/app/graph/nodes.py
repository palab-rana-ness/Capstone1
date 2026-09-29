"""LangGraph node functions.

Each node has exactly one responsibility and operates only on the generic
`AgentState`. No node imports SparkAdapter/SynapseAdapter directly, and no
node makes raw Chroma calls -- everything goes through the adapter
interface and the `IncidentMemoryRepository` interface.
"""
from __future__ import annotations

import logging

from app.adapters.registry import get_adapter
from app.config import get_settings
from app.graph.state import AgentState
from app.memory.base import IncidentMemoryRepository
from app.memory.chroma import get_default_repository
from app.models.incident import Incident
from app.models.remediation import RemediationValidationResult
from app.models.response import DiagnosisResponse
from app.services.diagnosis_service import diagnose_incident
from app.services.log_fetcher import LogFetcher, get_log_fetcher
from app.services.remediation_service import recommend_remediation
from app.utils.incident_formatter import build_memory_document, build_query_text

logger = logging.getLogger(__name__)


def validate_trigger(state: AgentState) -> dict:
    """Validate the incoming trigger and build the initial (log-less) incident.

    Structural validation (types, required fields) is already enforced by
    the `IncidentTrigger` Pydantic model. This node checks additional
    invariants and seeds the `Incident` that later nodes enrich.
    """
    trigger = state["trigger"]
    if not trigger.tenant_id.strip():
        raise ValueError("Trigger is missing a tenant_id")
    if not trigger.incident_id.strip():
        raise ValueError("Trigger is missing an incident_id")
    if not trigger.pipeline.strip():
        raise ValueError("Trigger is missing a pipeline")
    logger.info(
        "Validated trigger %s for tenant %s", trigger.incident_id, trigger.tenant_id
    )
    return {"incident": Incident.from_trigger(trigger)}


def resolve_adapter(state: AgentState) -> dict:
    """Resolve the pipeline adapter for this incident."""
    incident = state["incident"]
    adapter = get_adapter(incident.adapter)
    logger.info("Resolved adapter '%s' for incident %s", adapter.name, incident.incident_id)
    return {"adapter": adapter, "adapter_name": adapter.name}


def fetch_logs(state: AgentState, fetcher: LogFetcher | None = None) -> dict:
    """Fetch logs and error details for this incident from New Relic.

    This is the agent step that replaces the UI-supplied logs: it queries
    the observability backend and enriches the incident before diagnosis.
    """
    trigger = state["trigger"]
    incident = state["incident"]
    adapter = state["adapter"]
    log_fetcher = fetcher or get_log_fetcher()

    result = log_fetcher.fetch_logs(trigger)
    enriched_incident = incident.model_copy(
        update={
            "error_message": result.error_message,
            "logs": result.logs,
            "details": {**incident.details, **result.details},
        }
    )
    normalized_incident = adapter.normalize_incident(enriched_incident)
    logger.info(
        "Fetched %d log lines from New Relic for incident %s",
        len(result.logs),
        incident.incident_id,
    )
    return {"incident": normalized_incident}


def validate_incident(state: AgentState) -> dict:
    """Validate the enriched incident's business-level invariants.

    Runs after `fetch_logs`, so this is where we confirm New Relic actually
    returned enough information to diagnose the failure.
    """
    incident = state["incident"]
    if not incident.tenant_id.strip():
        raise ValueError("Incident is missing a tenant_id")
    if not incident.incident_id.strip():
        raise ValueError("Incident is missing an incident_id")
    if not incident.error_message.strip():
        raise ValueError("Incident is missing an error_message")
    logger.info(
        "Validated incident %s for tenant %s", incident.incident_id, incident.tenant_id
    )
    return {}


def retrieve_similar_incidents(
    state: AgentState, repository: IncidentMemoryRepository | None = None
) -> dict:
    """Retrieve similar historical incidents, scoped strictly to the tenant."""
    incident = state["incident"]
    repo = repository or get_default_repository()
    settings = get_settings()

    query_text = build_query_text(incident)
    similar = repo.find_similar_incidents(
        tenant_id=incident.tenant_id,
        query_text=query_text,
        adapter=incident.adapter,
        top_k=settings.similar_incidents_top_k,
    )
    logger.info(
        "Retrieved %d similar incidents for tenant %s", len(similar), incident.tenant_id
    )
    return {"similar_incidents": similar}


def diagnose_failure(state: AgentState) -> dict:
    """Run the diagnosis LLM step using adapter context + similar incidents."""
    incident = state["incident"]
    adapter = state["adapter"]
    similar_incidents = state.get("similar_incidents", [])

    adapter_context = adapter.build_diagnosis_context(incident)
    diagnosis = diagnose_incident(incident, adapter_context, similar_incidents)

    return {"adapter_context": adapter_context, "diagnosis": diagnosis}


def generate_remediation(state: AgentState) -> dict:
    """Run the remediation LLM step, constrained to adapter-allowed actions."""
    incident = state["incident"]
    adapter = state["adapter"]
    diagnosis = state["diagnosis"]
    similar_incidents = state.get("similar_incidents", [])

    allowed_actions = adapter.get_allowed_remediation_actions()
    remedies = recommend_remediation(
        incident, diagnosis, allowed_actions, similar_incidents
    )
    return {"remediation": remedies}


def validate_remediation(state: AgentState) -> dict:
    """Deterministically validate LLM-proposed remediation actions.

    The LLM is never trusted blindly: any action outside the adapter's
    allow-list is rejected, and diagnoses with high confidence must be
    backed by non-empty evidence.
    """
    incident = state["incident"]
    adapter = state["adapter"]
    diagnosis = state["diagnosis"]
    remedies = state.get("remediation", [])

    allowed_actions = set(adapter.get_allowed_remediation_actions())
    result = RemediationValidationResult()

    if not incident.tenant_id or not incident.incident_id:
        raise ValueError("Cannot validate remediation without tenant_id/incident_id")

    if diagnosis.confidence >= 0.7 and not diagnosis.evidence:
        raise ValueError("High-confidence diagnosis must include supporting evidence")

    for remedy in remedies:
        if remedy.action not in allowed_actions:
            result.rejected_actions.append(remedy.action)
            result.reasons[remedy.action] = (
                f"Action '{remedy.action}' is not allowed for adapter "
                f"'{adapter.name}'"
            )
            continue
        if not remedy.explanation or not remedy.risk:
            result.rejected_actions.append(remedy.action)
            result.reasons[remedy.action] = "Missing explanation or risk fields"
            continue
        result.valid_actions.append(remedy)

    return {"validation_result": result, "remediation": result.valid_actions}


def store_incident_memory(
    state: AgentState, repository: IncidentMemoryRepository | None = None
) -> dict:
    """Persist the diagnosed incident into the AI incident memory store."""
    incident = state["incident"]
    diagnosis = state["diagnosis"]
    remedies = state.get("remediation", [])
    repo = repository or get_default_repository()

    document_text = build_memory_document(incident, diagnosis, remedies)
    resolution = "; ".join(r.action for r in remedies) or None

    repo.update_incident(
        incident=incident,
        document_text=document_text,
        status="diagnosed",
        extra_metadata={
            "root_cause": diagnosis.root_cause,
            "resolution": resolution,
        },
    )
    logger.info("Stored incident memory for %s", incident.incident_id)
    return {}


def build_response(state: AgentState) -> dict:
    """Assemble the final structured response returned to the Reflex UI."""
    incident = state["incident"]
    diagnosis = state["diagnosis"]
    remedies = state.get("remediation", [])
    similar_incidents = state.get("similar_incidents", [])

    message_for_ui = (
        f"The {incident.adapter} pipeline failed during "
        f"{diagnosis.failure_location}. The most probable cause is "
        f"{diagnosis.root_cause}."
    )

    response = DiagnosisResponse(
        tenant_id=incident.tenant_id,
        incident_id=incident.incident_id,
        adapter=incident.adapter,
        pipeline=incident.pipeline,
        failure_location=diagnosis.failure_location,
        root_cause=diagnosis.root_cause,
        confidence=diagnosis.confidence,
        evidence=diagnosis.evidence,
        recent_logs=incident.logs[-100:],
        similar_incidents=similar_incidents,
        remedies=remedies,
        message_for_ui=message_for_ui,
    )
    return {"final_response": response}
