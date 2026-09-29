"""Tests for the LangGraph incident-diagnosis workflow."""
from __future__ import annotations

import pytest

from app.adapters.registry import UnknownAdapterError
from app.graph.nodes import validate_incident
from app.graph.workflow import get_incident_diagnosis_graph
from app.models.incident import Incident
from app.services.log_fetcher import LogFetchResult
from tests.conftest import FakeLogFetcher, make_spark_trigger


def test_full_graph_run_valid_spark_incident(
    patch_llm_services, patch_memory_repo, patch_log_fetcher
):
    trigger = make_spark_trigger()
    graph = get_incident_diagnosis_graph()

    result = graph.invoke({"trigger": trigger})

    response = result["final_response"]
    assert response.tenant_id == "tenant_001"
    assert response.incident_id == "INC_12345"
    assert response.adapter == "spark"
    assert response.root_cause == "Spark executor memory exhaustion during aggregation"
    assert response.confidence == pytest.approx(0.9)
    assert len(response.remedies) == 1
    assert response.remedies[0].action == "increase_executor_memory"
    assert "aggregate_customer_data" in response.message_for_ui

    # Verify the incident was stored in memory as a side effect.
    stored = patch_memory_repo.get_incident(trigger.tenant_id, trigger.incident_id)
    assert stored is not None
    assert stored["metadata"]["status"] == "diagnosed"


def test_graph_raises_for_unknown_adapter(patch_llm_services, patch_memory_repo):
    trigger = make_spark_trigger(adapter="unknown_tech")
    graph = get_incident_diagnosis_graph()

    with pytest.raises(UnknownAdapterError):
        graph.invoke({"trigger": trigger})


def test_validate_incident_rejects_blank_tenant_id():
    incident = Incident.model_construct(
        tenant_id="   ",
        incident_id="INC_1",
        adapter="spark",
        pipeline="p",
        status="FAILED",
        failed_stage=None,
        failed_task=None,
        error_message="boom",
        logs=[],
        details={},
        metadata={},
    )
    with pytest.raises(ValueError):
        validate_incident({"incident": incident})


def test_shuffle_failure_diagnosis(monkeypatch, patch_memory_repo):
    import app.graph.nodes as nodes_module
    from app.models.diagnosis import Diagnosis
    from app.models.remediation import RemediationAction

    shuffle_diagnosis = Diagnosis(
        failure_location="shuffle_join",
        root_cause="Shuffle fetch failure due to lost executor",
        confidence=0.85,
        evidence=["FetchFailedException", "Executor lost"],
        reasoning_summary="Fetch failure indicates a lost executor during shuffle.",
    )
    remedy = RemediationAction(
        action="increase_shuffle_partitions",
        explanation="Reduce shuffle block size to avoid fetch failures.",
        priority="medium",
        risk="Additional shuffle overhead.",
        requires_approval=True,
    )

    monkeypatch.setattr(
        nodes_module,
        "diagnose_incident",
        lambda incident, adapter_context, similar_incidents, llm=None: shuffle_diagnosis,
    )
    monkeypatch.setattr(
        nodes_module,
        "recommend_remediation",
        lambda incident, diagnosis, allowed_actions, similar_incidents, llm=None: [remedy],
    )
    monkeypatch.setattr(
        nodes_module,
        "get_log_fetcher",
        lambda: FakeLogFetcher(
            LogFetchResult(
                error_message="org.apache.spark.shuffle.FetchFailedException",
                logs=["Shuffle fetch started", "FetchFailedException", "Executor lost"],
            )
        ),
    )

    trigger = make_spark_trigger(incident_id="INC_SHUFFLE", failed_stage="shuffle_join")
    graph = get_incident_diagnosis_graph()
    result = graph.invoke({"trigger": trigger})

    response = result["final_response"]
    assert response.failure_location == "shuffle_join"
    assert "Shuffle fetch failure" in response.root_cause
    assert response.remedies[0].action == "increase_shuffle_partitions"


def test_unsupported_remediation_is_rejected(
    monkeypatch, patch_memory_repo, patch_log_fetcher, oom_diagnosis
):
    import app.graph.nodes as nodes_module
    from app.models.remediation import RemediationAction

    bogus_remedy = RemediationAction(
        action="delete_production_database",
        explanation="Not a real allowed action.",
        priority="high",
        risk="Catastrophic.",
        requires_approval=True,
    )

    monkeypatch.setattr(
        nodes_module,
        "diagnose_incident",
        lambda incident, adapter_context, similar_incidents, llm=None: oom_diagnosis,
    )
    monkeypatch.setattr(
        nodes_module,
        "recommend_remediation",
        lambda incident, diagnosis, allowed_actions, similar_incidents, llm=None: [bogus_remedy],
    )

    trigger = make_spark_trigger()
    graph = get_incident_diagnosis_graph()
    result = graph.invoke({"trigger": trigger})

    response = result["final_response"]
    assert response.remedies == []
    assert "delete_production_database" in result["validation_result"].rejected_actions
