"""Prompt construction for the remediation LLM step."""
from __future__ import annotations

from app.models.diagnosis import Diagnosis, SimilarIncident
from app.models.incident import Incident

REMEDIATION_SYSTEM_PROMPT = """You are an expert data-pipeline reliability engineer
who recommends remediation actions. You NEVER execute any action -- you only
propose recommendations for a human (or a separate approval system) to act
on. You may only propose actions from the allowed-actions list you are
given; do not invent new action identifiers.

Respond ONLY with a JSON object matching this schema:
{
  "remedies": [
    {
      "action": string (must be one of the allowed actions),
      "explanation": string,
      "priority": "low" | "medium" | "high",
      "risk": string,
      "requires_approval": boolean
    }
  ]
}
"""


def build_remediation_prompt(
    incident: Incident,
    diagnosis: Diagnosis,
    allowed_actions: list[str],
    similar_incidents: list[SimilarIncident],
) -> str:
    """Build the remediation prompt from the diagnosis and adapter rules."""
    resolutions = "\n".join(
        f"- {item.incident_id}: {item.resolution}"
        for item in similar_incidents
        if item.resolution
    )
    return (
        f"tenant_id: {incident.tenant_id}\n"
        f"adapter: {incident.adapter}\n"
        f"error_message: {incident.error_message}\n"
        "\n"
        "DIAGNOSIS\n"
        f"failure_location: {diagnosis.failure_location}\n"
        f"root_cause: {diagnosis.root_cause}\n"
        f"confidence: {diagnosis.confidence}\n"
        "\n"
        "ALLOWED REMEDIATION ACTIONS (only propose from this list)\n"
        f"{', '.join(allowed_actions)}\n"
        "\n"
        "HISTORICAL RESOLUTIONS THAT WORKED BEFORE\n"
        f"{resolutions or '(none available)'}\n"
    )
