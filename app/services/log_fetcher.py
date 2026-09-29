"""Retrieves incident logs/error details from New Relic.

Replaces the old flow where the UI collected logs up front: the UI now only
sends an `IncidentTrigger` (tenant, incident, adapter, pipeline + hints),
and this module is the "agent" that goes and pulls the actual logs from New
Relic before diagnosis runs.

The exact NRQL query per adapter/pipeline is owned by the observability
teammate; `NewRelicLogFetcher._build_nrql` is the intended extension point
for that work. This module provides a working NerdGraph client and a stable
`LogFetcher` interface so the rest of the graph never depends on New Relic
directly.
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod

import httpx
from pydantic import BaseModel, Field

from app.config import get_settings
from app.models.incident import IncidentTrigger

logger = logging.getLogger(__name__)


class LogFetchResult(BaseModel):
    """Everything the diagnosis step needs, as retrieved from New Relic."""

    error_message: str = Field(default="")
    logs: list[str] = Field(default_factory=list)
    details: dict = Field(default_factory=dict)


class LogFetcher(ABC):
    """Abstract interface for retrieving incident logs from an observability backend."""

    @abstractmethod
    def fetch_logs(self, trigger: IncidentTrigger) -> LogFetchResult:
        """Fetch logs and error details for the given incident trigger."""


class NewRelicLogFetcher(LogFetcher):
    """New Relic NerdGraph-backed implementation of `LogFetcher`."""

    def __init__(
        self,
        api_key: str,
        account_id: str,
        graphql_endpoint: str,
        lookback_minutes: int,
        log_limit: int,
    ) -> None:
        self._api_key = api_key
        self._account_id = account_id
        self._graphql_endpoint = graphql_endpoint
        self._lookback_minutes = lookback_minutes
        self._log_limit = log_limit

    def _build_nrql(self, trigger: IncidentTrigger) -> str:
        """Build the NRQL query used to pull this pipeline's log lines.

        Filters on `pipeline_id` only (the trigger's `pipeline` maps to
        `pipeline_id`), returning logs across all runs of that pipeline
        within the lookback window, not just the one tied to this incident.
        """
        return (
            "SELECT message, timestamp FROM Log "
            f"WHERE pipeline_id = '{trigger.pipeline}' "
            f"SINCE {self._lookback_minutes} MINUTES AGO "
            f"ORDER BY timestamp DESC "
            f"LIMIT {self._log_limit}"
        )

    def fetch_logs(self, trigger: IncidentTrigger) -> LogFetchResult:
        if not self._api_key or not self._account_id:
            raise RuntimeError(
                "New Relic is not configured (missing NEWRELIC_API_KEY/"
                "NEWRELIC_ACCOUNT_ID)"
            )

        nrql = self._build_nrql(trigger)
        query = """
        query ($accountId: Int!, $nrql: Nrql!) {
          actor {
            account(id: $accountId) {
              nrql(query: $nrql) {
                results
              }
            }
          }
        }
        """
        variables = {"accountId": int(self._account_id), "nrql": nrql}

        try:
            response = httpx.post(
                self._graphql_endpoint,
                json={"query": query, "variables": variables},
                headers={"API-Key": self._api_key, "Content-Type": "application/json"},
                timeout=30.0,
            )
            response.raise_for_status()
            payload = response.json()
        except httpx.HTTPError as exc:
            logger.exception("New Relic log fetch failed for incident %s", trigger.incident_id)
            raise RuntimeError("Failed to fetch logs from New Relic") from exc

        results = (
            payload.get("data", {})
            .get("actor", {})
            .get("account", {})
            .get("nrql", {})
            .get("results", [])
        )

        # Results come back newest-first (ORDER BY timestamp DESC); reverse
        # so `logs` reads oldest-to-newest and the latest event is logs[-1].
        logs = [row.get("message", "") for row in reversed(results) if row.get("message")]
        error_message = logs[-1] if logs else ""
        return LogFetchResult(error_message=error_message, logs=logs, details={"nrql": nrql})


_default_fetcher: LogFetcher | None = None


def get_log_fetcher() -> LogFetcher:
    """Return a process-wide cached `LogFetcher` instance."""
    global _default_fetcher
    if _default_fetcher is None:
        settings = get_settings()
        _default_fetcher = NewRelicLogFetcher(
            api_key=settings.newrelic_api_key,
            account_id=settings.newrelic_account_id,
            graphql_endpoint=settings.newrelic_graphql_endpoint,
            lookback_minutes=settings.newrelic_log_lookback_minutes,
            log_limit=settings.newrelic_log_limit,
        )
    return _default_fetcher
