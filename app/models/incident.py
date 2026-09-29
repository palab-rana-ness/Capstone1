"""Pydantic models describing an incoming pipeline failure incident."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator


class IncidentTrigger(BaseModel):
    """The minimal payload the UI sends to kick off the diagnosis graph.

    No logs or error details are collected by the UI anymore -- the graph
    fetches those itself from New Relic. This only carries the identifiers
    and hints needed to locate the incident in the observability backend.
    """

    tenant_id: str = Field(..., min_length=1)
    incident_id: str = Field(..., min_length=1)
    adapter: str = Field(..., min_length=1)
    pipeline: str = Field(..., min_length=1)
    status: str | None = None
    failed_stage: str | None = None
    failed_task: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    details: dict[str, Any] = Field(default_factory=dict)

    @field_validator("adapter")
    @classmethod
    def normalize_adapter_name(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("tenant_id", "incident_id")
    @classmethod
    def strip_ids(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be blank")
        return stripped


class Incident(BaseModel):
    """A technology-agnostic representation of a failed pipeline run.

    Built from an `IncidentTrigger` and then enriched in-graph with logs
    and error details fetched from New Relic. This model only validates
    structure, it does not fetch any additional data from external systems.
    """

    tenant_id: str = Field(..., min_length=1)
    incident_id: str = Field(..., min_length=1)
    adapter: str = Field(..., min_length=1)
    pipeline: str = Field(..., min_length=1)
    status: str = Field(..., min_length=1)
    failed_stage: str | None = None
    failed_task: str | None = None
    error_message: str = Field(default="")
    logs: list[str] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("adapter")
    @classmethod
    def normalize_adapter_name(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("tenant_id", "incident_id")
    @classmethod
    def strip_ids(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be blank")
        return stripped

    @classmethod
    def from_trigger(cls, trigger: IncidentTrigger) -> "Incident":
        """Build a bare incident from a trigger, before logs are fetched."""
        return cls(
            tenant_id=trigger.tenant_id,
            incident_id=trigger.incident_id,
            adapter=trigger.adapter,
            pipeline=trigger.pipeline,
            status=trigger.status or "FAILED",
            failed_stage=trigger.failed_stage,
            failed_task=trigger.failed_task,
            error_message="",
            logs=[],
            details=dict(trigger.details),
            metadata=dict(trigger.metadata),
        )
