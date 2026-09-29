"""Mandatory tenant isolation tests for incident memory retrieval."""
from __future__ import annotations

from tests.conftest import make_spark_incident


def test_tenant_a_never_retrieves_tenant_b_incidents(chroma_repo):
    tenant_a_incident = make_spark_incident(tenant_id="tenant_001", incident_id="INC_A1")
    tenant_b_incident = make_spark_incident(tenant_id="tenant_002", incident_id="INC_B1")

    chroma_repo.add_incident(
        tenant_a_incident,
        "Pipeline: customer_daily_pipeline\nError: java.lang.OutOfMemoryError: Java heap space",
        status="resolved",
        extra_metadata={"root_cause": "OOM", "resolution": "increase_executor_memory"},
    )
    chroma_repo.add_incident(
        tenant_b_incident,
        "Pipeline: customer_daily_pipeline\nError: java.lang.OutOfMemoryError: Java heap space",
        status="resolved",
        extra_metadata={"root_cause": "OOM", "resolution": "increase_executor_memory"},
    )

    results_for_a = chroma_repo.find_similar_incidents(
        tenant_id="tenant_001",
        query_text="OutOfMemoryError Java heap space",
        adapter="spark",
        top_k=5,
    )
    results_for_b = chroma_repo.find_similar_incidents(
        tenant_id="tenant_002",
        query_text="OutOfMemoryError Java heap space",
        adapter="spark",
        top_k=5,
    )

    assert all(r.incident_id != "INC_B1" for r in results_for_a)
    assert all(r.incident_id != "INC_A1" for r in results_for_b)
    assert any(r.incident_id == "INC_A1" for r in results_for_a)
    assert any(r.incident_id == "INC_B1" for r in results_for_b)


def test_get_incident_is_tenant_scoped(chroma_repo):
    incident = make_spark_incident(tenant_id="tenant_001", incident_id="INC_SHARED")
    chroma_repo.add_incident(incident, "doc", status="resolved")

    # Same incident_id under a different tenant must not resolve to tenant_001's data.
    assert chroma_repo.get_incident("tenant_002", "INC_SHARED") is None
    assert chroma_repo.get_incident("tenant_001", "INC_SHARED") is not None
