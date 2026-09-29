"""Typed state shared across all LangGraph nodes."""
from __future__ import annotations

from typing import TypedDict

from app.adapters.base import PipelineAdapter
from app.models.diagnosis import Diagnosis, SimilarIncident
from app.models.incident import Incident, IncidentTrigger
from app.models.remediation import RemediationAction, RemediationValidationResult
from app.models.response import DiagnosisResponse


class AgentState(TypedDict, total=False):
    """State threaded through the incident-diagnosis LangGraph.

    Only `trigger` is required at the start; every other key is populated
    incrementally as the graph progresses through its nodes.
    """

    trigger: IncidentTrigger
    incident: Incident
    adapter_name: str
    adapter: PipelineAdapter
    adapter_context: str
    similar_incidents: list[SimilarIncident]
    diagnosis: Diagnosis
    remediation: list[RemediationAction]
    validation_result: RemediationValidationResult
    final_response: DiagnosisResponse
