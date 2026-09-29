"""Tests for the SparkAdapter implementation."""
from __future__ import annotations

from app.adapters.registry import UnknownAdapterError, get_adapter, list_adapters
from app.adapters.spark import SparkAdapter
from tests.conftest import make_spark_incident


def test_spark_adapter_registered():
    assert "spark" in list_adapters()
    adapter = get_adapter("spark")
    assert isinstance(adapter, SparkAdapter)


def test_unknown_adapter_raises():
    try:
        get_adapter("does_not_exist")
        assert False, "expected UnknownAdapterError"
    except UnknownAdapterError:
        pass


def test_spark_allowed_actions_include_expected_set():
    adapter = SparkAdapter()
    actions = adapter.get_allowed_remediation_actions()
    for expected in ["increase_executor_memory", "retry_pipeline", "handle_data_skew"]:
        assert expected in actions


def test_spark_failure_patterns_cover_oom_and_shuffle():
    adapter = SparkAdapter()
    names = {p.name for p in adapter.get_failure_patterns()}
    assert "executor_out_of_memory" in names
    assert "shuffle_fetch_failure" in names
    assert "data_skew" in names


def test_spark_build_diagnosis_context_includes_details():
    adapter = SparkAdapter()
    incident = make_spark_incident()
    context = adapter.build_diagnosis_context(incident)
    assert "Spark" in context
    assert "executor_memory" in context
    assert "increase_executor_memory" in context


def test_spark_normalize_incident_strips_log_lines():
    adapter = SparkAdapter()
    incident = make_spark_incident(logs=["  padded line  ", "", "clean"])
    normalized = adapter.normalize_incident(incident)
    assert normalized.logs == ["padded line", "clean"]
