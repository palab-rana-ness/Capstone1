"""Helpers for turning an Incident into semantically meaningful text."""
from __future__ import annotations

from app.models.diagnosis import Diagnosis
from app.models.incident import Incident
from app.models.remediation import RemediationAction


def build_query_text(incident: Incident) -> str:
    """Build the text used to search for similar historical incidents."""
    logs_text = "\n".join(incident.logs[-10:])
    details_text = ", ".join(f"{k}={v}" for k, v in incident.details.items())
    return (
        f"Pipeline: {incident.pipeline}\n"
        f"Adapter: {incident.adapter}\n"
        f"Failed stage: {incident.failed_stage or 'unknown'}\n"
        f"Failed task: {incident.failed_task or 'unknown'}\n"
        f"Error: {incident.error_message}\n"
        f"Logs:\n{logs_text}\n"
        f"Details: {details_text}"
    )


def build_memory_document(
    incident: Incident,
    diagnosis: Diagnosis | None = None,
    remedies: list[RemediationAction] | None = None,
) -> str:
    """Build the full semantic document stored in Chroma for this incident."""
    logs_text = "\n".join(incident.logs)
    details_text = "\n".join(f"{k}={v}" for k, v in incident.details.items())

    lines = [
        f"Pipeline: {incident.pipeline}",
        "",
        f"Adapter: {incident.adapter}",
        "",
        f"Failed stage: {incident.failed_stage or 'unknown'}",
        "",
        "Error:",
        incident.error_message,
        "",
        "Logs:",
        logs_text or "(none)",
        "",
        "Details:",
        details_text or "(none)",
    ]

    if diagnosis is not None:
        lines += [
            "",
            "Diagnosis:",
            f"{diagnosis.root_cause} (failure location: {diagnosis.failure_location})",
        ]

    if remedies:
        remedy_text = "; ".join(r.action for r in remedies)
        lines += ["", "Recommended remediation:", remedy_text]

    return "\n".join(lines)
