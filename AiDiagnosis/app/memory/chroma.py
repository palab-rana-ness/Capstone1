"""ChromaDB-backed implementation of IncidentMemoryRepository."""
from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any

import chromadb
from chromadb.api.models.Collection import Collection

from app.memory.base import IncidentMemoryRepository
from app.models.diagnosis import SimilarIncident
from app.models.incident import Incident

logger = logging.getLogger(__name__)


class ChromaIncidentMemoryRepository(IncidentMemoryRepository):
    """Persists incident memory in a local, on-disk Chroma collection."""

    def __init__(self, persist_dir: str, collection_name: str) -> None:
        self._client = chromadb.PersistentClient(path=persist_dir)
        self._collection: Collection = self._client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def _doc_id(self, tenant_id: str, incident_id: str) -> str:
        return f"{tenant_id}::{incident_id}"

    def add_incident(
        self,
        incident: Incident,
        document_text: str,
        status: str,
        extra_metadata: dict[str, Any] | None = None,
    ) -> None:
        self._upsert(incident, document_text, status, extra_metadata)

    def update_incident(
        self,
        incident: Incident,
        document_text: str,
        status: str,
        extra_metadata: dict[str, Any] | None = None,
    ) -> None:
        self._upsert(incident, document_text, status, extra_metadata)

    def _upsert(
        self,
        incident: Incident,
        document_text: str,
        status: str,
        extra_metadata: dict[str, Any] | None,
    ) -> None:
        metadata: dict[str, Any] = {
            "tenant_id": incident.tenant_id,
            "incident_id": incident.incident_id,
            "adapter": incident.adapter,
            "pipeline": incident.pipeline,
            "status": status,
        }
        if extra_metadata:
            # Only allow flat, primitive metadata values (Chroma requirement).
            for key, value in extra_metadata.items():
                if isinstance(value, (str, int, float, bool)) or value is None:
                    metadata[key] = value
                else:
                    metadata[key] = str(value)

        doc_id = self._doc_id(incident.tenant_id, incident.incident_id)
        self._collection.upsert(
            ids=[doc_id],
            documents=[document_text],
            metadatas=[metadata],
        )

    def find_similar_incidents(
        self,
        tenant_id: str,
        query_text: str,
        adapter: str | None = None,
        top_k: int = 5,
    ) -> list[SimilarIncident]:
        # Tenant filtering happens INSIDE the similarity search via `where`,
        # never as a post-hoc filter over a global search.
        try:
            count = self._collection.count()
        except Exception:  # pragma: no cover - defensive
            count = 0
        if count == 0:
            return []
 
        fetch_n = max(top_k * 3, top_k)
        results = self._collection.query(
            query_texts=[query_text],
            n_results=min(fetch_n, count),
            where={"tenant_id": tenant_id},
        )

        ids = results.get("ids", [[]])[0]
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        candidates: list[SimilarIncident] = []
        for _doc_id, _document, metadata, distance in zip(
            ids, documents, metadatas, distances
        ):
            if metadata.get("tenant_id") != tenant_id:
                # Defensive double-check: never leak cross-tenant results.
                continue
            similarity = max(0.0, 1.0 - float(distance))
            candidates.append(
                SimilarIncident(
                    incident_id=metadata.get("incident_id", "unknown"),
                    similarity=round(min(similarity, 1.0), 4),
                    root_cause=metadata.get("root_cause"),
                    resolution=metadata.get("resolution"),
                    adapter=metadata.get("adapter"),
                    pipeline=metadata.get("pipeline"),
                )
            )

        def sort_key(item: SimilarIncident) -> tuple[int, float]:
            adapter_match = 1 if adapter and item.adapter == adapter else 0
            return (adapter_match, item.similarity)

        candidates.sort(key=sort_key, reverse=True)
        return candidates[:top_k]

    def get_incident(self, tenant_id: str, incident_id: str) -> dict[str, Any] | None:
        doc_id = self._doc_id(tenant_id, incident_id)
        result = self._collection.get(ids=[doc_id])
        ids = result.get("ids", [])
        if not ids:
            return None
        return {
            "id": ids[0],
            "document": result.get("documents", [None])[0],
            "metadata": result.get("metadatas", [None])[0],
        }


@lru_cache
def get_default_repository() -> ChromaIncidentMemoryRepository:
    """Return a process-wide cached repository built from app settings."""
    from app.config import get_settings

    settings = get_settings()
    return ChromaIncidentMemoryRepository(
        persist_dir=settings.chroma_persist_dir,
        collection_name=settings.chroma_collection_name,
    )

