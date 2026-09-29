"""Prompt construction for the diagnosis LLM step."""
from __future__ import annotations

from app.models.diagnosis import SimilarIncident
from app.models.incident import Incident

DIAGNOSIS_SYSTEM_PROMPT = """You are an expert data-pipeline reliability engineer.

You diagnose why a data pipeline failed, using only the information you are
given. You must never invent evidence that is not present in the incident
error message, logs, details, metadata, or the provided historical
incidents. Clearly separate observed facts from probable inference. If the
available evidence is insufficient to reach a confident conclusion, say so
explicitly and lower your confidence score accordingly.

Answer these questions:
1. Where did the pipeline fail?
2. What is the most probable root cause?
3. What evidence supports the diagnosis?
4. How confident are you (0.0-1.0)?
5. What information is missing, if any?

Respond ONLY with a JSON object matching this schema:
{
  "failure_location": string,
  "root_cause": string,
  "confidence": number between 0.0 and 1.0,
  "evidence": array of strings, each traceable to the incident or history,
  "reasoning_summary": string that also mentions any missing information
}
"""


def _format_similar_incidents(similar_incidents: list[SimilarIncident]) -> str:
    if not similar_incidents:
        return "(no similar historical incidents found)"
    lines = []
    for item in similar_incidents:
        lines.append(
            f"- incident_id={item.incident_id}, similarity={item.similarity:.2f}, "
            f"root_cause={item.root_cause or 'unknown'}, "
            f"resolution={item.resolution or 'unknown'}"
        )
    return "\n".join(lines)


def build_diagnosis_prompt(
    incident: Incident,
    adapter_context: str,
    similar_incidents: list[SimilarIncident],
) -> str:
    """Combine current incident + adapter context + history into one prompt."""
    details_text = "\n".join(f"- {k}: {v}" for k, v in incident.details.items())
    metadata_text = "\n".join(f"- {k}: {v}" for k, v in incident.metadata.items())
    logs_text = "\n".join(incident.logs)

    return (
        "CURRENT INCIDENT\n"
        f"tenant_id: {incident.tenant_id}\n"
        f"incident_id: {incident.incident_id}\n"
        f"pipeline: {incident.pipeline}\n"
        f"failed_stage: {incident.failed_stage or 'unknown'}\n"
        f"failed_task: {incident.failed_task or 'unknown'}\n"
        f"error_message: {incident.error_message}\n"
        f"logs:\n{logs_text or '(none)'}\n"
        f"details:\n{details_text or '(none)'}\n"
        f"metadata:\n{metadata_text or '(none)'}\n"
        "\n"
        "ADAPTER CONTEXT\n"
        f"{adapter_context}\n"
        "\n"
        "SIMILAR HISTORICAL INCIDENTS\n"
        f"{_format_similar_incidents(similar_incidents)}\n"
    )
