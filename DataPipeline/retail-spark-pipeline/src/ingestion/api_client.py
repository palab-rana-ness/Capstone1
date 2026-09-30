"""Thin HTTP client for the existing retail FastAPI mock source system.

Does not modify or reimplement the FastAPI server -- purely a consumer.
"""

from typing import Any, Optional

import requests

from src.config.config import Settings


class RetailAPIClient:
    """Wraps calls to the FastAPI retail mock APIs for a single tenant."""

    def __init__(self, settings: Settings, tenant_id: str):
        self.settings = settings
        self.tenant_id = tenant_id
        self._session = requests.Session()
        self._session.headers.update({"X-Tenant-ID": tenant_id})

    def get_page(
        self,
        path: str,
        limit: int,
        offset: int,
        updated_since: Optional[str] = None,
        extra_params: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Fetch a single page from a paginated list endpoint (raw envelope)."""
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if updated_since:
            params["updated_since"] = updated_since
        if extra_params:
            params.update(extra_params)

        url = f"{self.settings.fastapi_base_url}{path}"
        response = self._session.get(url, params=params, timeout=self.settings.api_timeout_seconds)
        response.raise_for_status()
        return response.json()

    def get_single(self, path: str) -> dict[str, Any]:
        """Fetch a single-record envelope, e.g. /products/{id}/promotions."""
        url = f"{self.settings.fastapi_base_url}{path}"
        response = self._session.get(url, timeout=self.settings.api_timeout_seconds)
        response.raise_for_status()
        return response.json()

    def close(self) -> None:
        self._session.close()
