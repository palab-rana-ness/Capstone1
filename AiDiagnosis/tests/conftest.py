"""Shared pytest fixtures."""
from __future__ import annotations

import pytest

from app.memory.chroma import ChromaIncidentMemoryRepository
from app.models.diagnosis import Diagnosis, SimilarIncident
from app.models.incident import Incident, IncidentTrigger
from app.models.remediation import RemediationAction
from app.services.log_fetcher import LogFetchResult


def make_spark_incident(**overrides) -> Incident:
    """Build a valid Spark OOM incident, with any fields overridden."""
    data = {
        "tenant_id": "tenant_001",
        "incident_id": "INC_12345",
        "adapter": "spark",
        "pipeline": "customer_daily_pipeline",
        "status": "FAILED",
        "failed_stage": "aggregate_customer_data",
        "failed_task": "task_17",
        "error_message": "java.lang.OutOfMemoryError: Java heap space",
        "logs": [
            "Stage 12 started",
            "ExecutorLostFailure",
            "Task 17 failed",
            "java.lang.OutOfMemoryError: Java heap space",
        ],
        "details": {
            "job_id": "spark_789",
            "executor_memory": "4g",
            "executor_cores": 2,
            "shuffle_read_mb": 8420,
        },
        "metadata": {"environment": "production", "region": "us-east-1"},
    }
    data.update(overrides)
    return Incident(**data)


def make_spark_trigger(**overrides) -> IncidentTrigger:
    """Build a minimal Spark OOM incident trigger, with fields overridden."""
    data = {
        "tenant_id": "tenant_001",
        "incident_id": "INC_12345",
        "adapter": "spark",
        "pipeline": "customer_daily_pipeline",
        "status": "FAILED",
        "failed_stage": "aggregate_customer_data",
        "failed_task": "task_17",
        "metadata": {"environment": "production", "region": "us-east-1"},
    }
    data.update(overrides)
    return IncidentTrigger(**data)


class FakeDiagnosisLLM:
    """Deterministic stand-in for the diagnosis LLM used in tests."""

    def __init__(self, diagnosis: Diagnosis) -> None:
        self._diagnosis = diagnosis

    def invoke(self, messages) -> Diagnosis:
        return self._diagnosis


class FakeRemediationList:
    def __init__(self, remedies: list[RemediationAction]) -> None:
        self.remedies = remedies


class FakeRemediationLLM:
    """Deterministic stand-in for the remediation LLM used in tests."""

    def __init__(self, remedies: list[RemediationAction]) -> None:
        self._remedies = remedies

    def invoke(self, messages):
        return FakeRemediationList(self._remedies)


@pytest.fixture
def oom_diagnosis() -> Diagnosis:
    return Diagnosis(
        failure_location="aggregate_customer_data",
        root_cause="Spark executor memory exhaustion during aggregation",
        confidence=0.9,
        evidence=["java.lang.OutOfMemoryError: Java heap space", "ExecutorLostFailure"],
        reasoning_summary="Heap error plus large shuffle volume indicates executor OOM.",
    )


@pytest.fixture
def oom_remedies() -> list[RemediationAction]:
    return [
        RemediationAction(
            action="increase_executor_memory",
            explanation="Executor memory appears insufficient for the workload.",
            priority="high",
            risk="Higher resource consumption and cost.",
            requires_approval=True,
        )
    ]


@pytest.fixture
def chroma_repo(tmp_path) -> ChromaIncidentMemoryRepository:
    return ChromaIncidentMemoryRepository(
        persist_dir=str(tmp_path / "chroma"),
        collection_name="incident_memory",
    )


@pytest.fixture
def patch_llm_services(monkeypatch, oom_diagnosis, oom_remedies):
    """Patch the graph's LLM-backed nodes with deterministic fakes."""
    import app.graph.nodes as nodes_module

    def fake_diagnose_incident(incident, adapter_context, similar_incidents, llm=None):
        return oom_diagnosis

    def fake_recommend_remediation(
        incident, diagnosis, allowed_actions, similar_incidents, llm=None
    ):
        return [r for r in oom_remedies if r.action in allowed_actions]

    monkeypatch.setattr(nodes_module, "diagnose_incident", fake_diagnose_incident)
    monkeypatch.setattr(nodes_module, "recommend_remediation", fake_recommend_remediation)
    return nodes_module


@pytest.fixture
def patch_memory_repo(monkeypatch, chroma_repo):
    """Patch the graph's memory access to use an isolated test repository."""
    import app.graph.nodes as nodes_module

    monkeypatch.setattr(nodes_module, "get_default_repository", lambda: chroma_repo)
    return chroma_repo


class FakeLogFetcher:
    """Deterministic stand-in for the New Relic log fetcher used in tests."""

    def __init__(self, result: LogFetchResult) -> None:
        self._result = result

    def fetch_logs(self, trigger) -> LogFetchResult:
        return self._result


@pytest.fixture
def oom_log_fetch_result() -> LogFetchResult:
    return LogFetchResult(
        error_message="java.lang.OutOfMemoryError: Java heap space",
        logs=[
            "Stage 12 started",
            "ExecutorLostFailure",
            "Task 17 failed",
            "java.lang.OutOfMemoryError: Java heap space",
        ],
        details={
            "job_id": "spark_789",
            "executor_memory": "4g",
            "executor_cores": 2,
            "shuffle_read_mb": 8420,
        },
    )


@pytest.fixture
def patch_log_fetcher(monkeypatch, oom_log_fetch_result):
    """Patch the graph's New Relic log fetch with a deterministic fake."""
    import app.graph.nodes as nodes_module

    fake_fetcher = FakeLogFetcher(oom_log_fetch_result)
    monkeypatch.setattr(nodes_module, "get_log_fetcher", lambda: fake_fetcher)
    return fake_fetcher
