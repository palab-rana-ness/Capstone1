"""Tests for the FastAPI HTTP layer."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import make_spark_trigger

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ai_diagnosis_valid_spark_incident(
    patch_llm_services, patch_memory_repo, patch_log_fetcher
):
    trigger = make_spark_trigger()
    response = client.post(
        "/api/v1/incidents/ai-diagnosis", json=trigger.model_dump()
    )
    assert response.status_code == 200
    body = response.json()
    assert body["tenant_id"] == "tenant_001"
    assert body["incident_id"] == "INC_12345"
    assert body["adapter"] == "spark"
    assert body["failure_location"] == "aggregate_customer_data"
    assert body["remedies"][0]["action"] == "increase_executor_memory"
    assert "message_for_ui" in body


def test_ai_diagnosis_invalid_incident_missing_fields():
    response = client.post(
        "/api/v1/incidents/ai-diagnosis",
        json={"tenant_id": "tenant_001"},
    )
    assert response.status_code == 422


def test_ai_diagnosis_unknown_adapter(patch_llm_services, patch_memory_repo, patch_log_fetcher):
    trigger = make_spark_trigger(adapter="unknown_tech")
    response = client.post(
        "/api/v1/incidents/ai-diagnosis", json=trigger.model_dump()
    )
    assert response.status_code == 400
