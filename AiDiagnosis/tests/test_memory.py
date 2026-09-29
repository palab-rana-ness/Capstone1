"""Tests for the Chroma-backed incident memory repository."""
from __future__ import annotations

from app.memory.chroma import ChromaIncidentMemoryRepository
from tests.conftest import make_spark_incident


def test_add_and_get_incident(chroma_repo: ChromaIncidentMemoryRepository):
    incident = make_spark_incident()
    chroma_repo.add_incident(
        incident=incident,
        document_text="Pipeline: customer_daily_pipeline\nError: OOM",
        status="diagnosed",
        extra_metadata={"root_cause": "OOM", "resolution": "increase_executor_memory"},
    )

    stored = chroma_repo.get_incident(incident.tenant_id, incident.incident_id)
    assert stored is not None
    assert stored["metadata"]["tenant_id"] == "tenant_001"
    assert stored["metadata"]["root_cause"] == "OOM"


def test_update_incident_overwrites_existing(chroma_repo: ChromaIncidentMemoryRepository):
    incident = make_spark_incident()
    chroma_repo.add_incident(incident, "first version", status="open")
    chroma_repo.update_incident(incident, "second version", status="diagnosed")

    stored = chroma_repo.get_incident(incident.tenant_id, incident.incident_id)
    assert stored["document"] == "second version"
    assert stored["metadata"]["status"] == "diagnosed"


def test_find_similar_incidents_ranks_by_similarity(chroma_repo):
    base = make_spark_incident()
    chroma_repo.add_incident(
        base.model_copy(update={"incident_id": "INC_A"}),
        "Pipeline: customer_daily_pipeline\nError: java.lang.OutOfMemoryError: Java heap space",
        status="resolved",
        extra_metadata={"root_cause": "OOM", "resolution": "increase_executor_memory"},
    )
    chroma_repo.add_incident(
        base.model_copy(update={"incident_id": "INC_B"}),
        "Pipeline: unrelated_pipeline\nError: connection refused to source database",
        status="resolved",
        extra_metadata={"root_cause": "connection failure", "resolution": "verify_source_connection"},
    )

    results = chroma_repo.find_similar_incidents(
        tenant_id="tenant_001",
        query_text="OutOfMemoryError Java heap space executor",
        adapter="spark",
        top_k=2,
    )
    assert len(results) == 2
    assert results[0].incident_id == "INC_A"


def test_chroma_persistence_across_instances(tmp_path):
    persist_dir = str(tmp_path / "chroma")
    repo1 = ChromaIncidentMemoryRepository(persist_dir, "incident_memory")
    incident = make_spark_incident()
    repo1.add_incident(incident, "persisted document", status="diagnosed")

    repo2 = ChromaIncidentMemoryRepository(persist_dir, "incident_memory")
    stored = repo2.get_incident(incident.tenant_id, incident.incident_id)
    assert stored is not None
    assert stored["document"] == "persisted document"
