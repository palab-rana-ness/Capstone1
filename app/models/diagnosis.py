"""Pydantic models for similar-incident retrieval and LLM diagnosis output."""
from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class SimilarIncident(BaseModel):
    """A historical incident retrieved from the incident memory store."""

    incident_id: str
    similarity: float = Field(..., ge=0.0, le=1.0)
    root_cause: str | None = None
    resolution: str | None = None
    adapter: str | None = None
    pipeline: str | None = None


class Diagnosis(BaseModel):
    """Structured output produced by the diagnosis LLM step.

    Every entry in `evidence` must be traceable back to the incident's
    error_message, logs, details, metadata, or similar historical incidents.
    """

    failure_location: str
    root_cause: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    evidence: list[str] = Field(default_factory=list)
    reasoning_summary: str

    @field_validator("confidence")
    @classmethod
    def clamp_confidence(cls, value: float) -> float:
        return max(0.0, min(1.0, value))
