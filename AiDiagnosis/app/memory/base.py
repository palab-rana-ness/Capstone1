"""Interface for the AI incident memory store.

All Chroma-specific calls must stay behind this interface. LangGraph nodes
depend only on `IncidentMemoryRepository`, never on ChromaDB directly.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.models.diagnosis import SimilarIncident
from app.models.incident import Incident


class IncidentMemoryRepository(ABC):
    """Abstract repository for storing and retrieving incident memory."""

    @abstractmethod
    def add_incident(
        self,
        incident: Incident,
        document_text: str,
        status: str,
        extra_metadata: dict[str, Any] | None = None,
    ) -> None:
        """Store a new incident document with its metadata."""

    @abstractmethod
    def update_incident(
        self,
        incident: Incident,
        document_text: str,
        status: str,
        extra_metadata: dict[str, Any] | None = None,
    ) -> None:
        """Update (or insert) an existing incident's document/metadata."""

    @abstractmethod
    def find_similar_incidents(
        self,
        tenant_id: str,
        query_text: str,
        adapter: str | None = None,
        top_k: int = 5,
    ) -> list[SimilarIncident]:
        """Find similar incidents scoped to a tenant.

        The tenant filter MUST be applied as part of the similarity search
        itself (via metadata filtering), never as a post-hoc filter over a
        global search.
        """

    @abstractmethod
    def get_incident(self, tenant_id: str, incident_id: str) -> dict[str, Any] | None:
        """Fetch a single stored incident record by tenant and incident id."""
