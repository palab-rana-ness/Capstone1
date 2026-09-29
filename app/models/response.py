"""Pydantic models for the final API response returned to the Reflex UI."""
from __future__ import annotations

from pydantic import BaseModel, Field

from app.models.diagnosis import SimilarIncident
from app.models.remediation import RemediationAction


class DiagnosisResponse(BaseModel):
    """The structured payload returned by POST /api/v1/incidents/ai-diagnosis."""

    tenant_id: str
    incident_id: str
    adapter: str
    pipeline: str

    failure_location: str
    root_cause: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    evidence: list[str] = Field(default_factory=list)
    recent_logs: list[str] = Field(default_factory=list)

    similar_incidents: list[SimilarIncident] = Field(default_factory=list)
    remedies: list[RemediationAction] = Field(default_factory=list)

    message_for_ui: str
