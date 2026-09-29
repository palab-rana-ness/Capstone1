"""RetailAPIClient tests using a mocked HTTP layer (no live server / Spark required)."""

from unittest.mock import MagicMock

from src.config.config import get_settings
from src.ingestion.api_client import RetailAPIClient


def _fake_response(payload: dict):
    response = MagicMock()
    response.json.return_value = payload
    response.raise_for_status.return_value = None
    return response


def test_get_page_sends_tenant_header_and_params(monkeypatch):
    settings = get_settings()
    client = RetailAPIClient(settings, "tenant_001")

    captured = {}

    def fake_get(url, params=None, timeout=None):
        captured["url"] = url
        captured["params"] = params
        captured["headers"] = client._session.headers
        return _fake_response({"data": [], "pagination": {"has_more": False}})

    monkeypatch.setattr(client._session, "get", fake_get)
    client.get_page("/api/v1/products", limit=50, offset=0)

    assert captured["headers"]["X-Tenant-ID"] == "tenant_001"
    assert captured["params"] == {"limit": 50, "offset": 0}
    assert captured["url"].endswith("/api/v1/products")


def test_get_page_includes_updated_since_when_provided(monkeypatch):
    settings = get_settings()
    client = RetailAPIClient(settings, "tenant_001")

    captured = {}

    def fake_get(url, params=None, timeout=None):
        captured["params"] = params
        return _fake_response({"data": [], "pagination": {"has_more": False}})

    monkeypatch.setattr(client._session, "get", fake_get)
    client.get_page("/api/v1/products", limit=50, offset=0, updated_since="2026-09-24T00:00:00Z")

    assert captured["params"]["updated_since"] == "2026-09-24T00:00:00Z"
