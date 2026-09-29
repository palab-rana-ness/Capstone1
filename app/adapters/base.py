"""Adapter interface: the only place pipeline-technology knowledge may live.

The LangGraph nodes must never import SparkAdapter or SynapseAdapter
directly -- they only depend on this abstract interface, resolved through
the adapter registry.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.models.incident import Incident


class FailurePattern:
    """A named, adapter-specific failure signature used during diagnosis."""

    def __init__(self, name: str, description: str, indicators: list[str]) -> None:
        self.name = name
        self.description = description
        self.indicators = indicators

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "indicators": self.indicators,
        }


class PipelineAdapter(ABC):
    """Common interface every pipeline-technology adapter must implement."""

    name: str

    @abstractmethod
    def normalize_incident(self, incident: Incident) -> Incident:
        """Return an incident with adapter-specific normalization applied.

        For example, trimming noisy log lines or standardizing field
        casing. Must not mutate the input incident.
        """

    @abstractmethod
    def get_failure_patterns(self) -> list[FailurePattern]:
        """Return the known failure patterns this adapter can recognize."""

    @abstractmethod
    def get_allowed_remediation_actions(self) -> list[str]:
        """Return the remediation action identifiers allowed for this adapter."""

    @abstractmethod
    def build_diagnosis_context(self, incident: Incident) -> str:
        """Build adapter-specific context text to feed into the diagnosis prompt."""
