"""Synapse adapter: a minimal prototype proving adapter independence.

This is intentionally incomplete. It exists only to demonstrate that the
LangGraph and diagnosis pipeline work with a second pipeline technology
without any changes to the graph itself.
"""
from __future__ import annotations

from app.adapters.base import FailurePattern, PipelineAdapter
from app.models.incident import Incident

_ALLOWED_ACTIONS: list[str] = [
    "retry_pipeline",
    "verify_source_connection",
    "verify_target_connection",
]

_FAILURE_PATTERNS: list[FailurePattern] = [
    FailurePattern(
        name="pipeline_timeout",
        description="A Synapse pipeline activity exceeded its configured timeout.",
        indicators=["timeout", "TimedOut"],
    ),
    FailurePattern(
        name="linked_service_failure",
        description="A Synapse linked service could not be reached.",
        indicators=["linked service", "connection", "unreachable"],
    ),
]


class SynapseAdapter(PipelineAdapter):
    """Prototype adapter for Azure Synapse pipelines (not fully implemented)."""

    name = "synapse"

    def normalize_incident(self, incident: Incident) -> Incident:
        normalized_logs = [line.strip() for line in incident.logs if line.strip()]
        return incident.model_copy(update={"logs": normalized_logs})

    def get_failure_patterns(self) -> list[FailurePattern]:
        return list(_FAILURE_PATTERNS)

    def get_allowed_remediation_actions(self) -> list[str]:
        return list(_ALLOWED_ACTIONS)

    def build_diagnosis_context(self, incident: Incident) -> str:
        patterns_text = "\n".join(
            f"- {p.name}: {p.description} (indicators: {', '.join(p.indicators)})"
            for p in self.get_failure_patterns()
        )
        return (
            "Adapter: Synapse (prototype)\n"
            "Known Synapse failure patterns:\n"
            f"{patterns_text}\n\n"
            "Allowed remediation actions for this adapter:\n"
            f"{', '.join(self.get_allowed_remediation_actions())}"
        )
