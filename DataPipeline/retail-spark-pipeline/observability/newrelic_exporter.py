"""Thin wrapper around the New Relic Python agent for background pipeline telemetry.

The agent is initialized once, as early as possible, in run_pipeline.py via
newrelic.agent.initialize("newrelic.ini"). Everything here just talks to that
already-running agent instance -- no OpenTelemetry SDK/OTLP wiring required.
"""

from __future__ import annotations

from typing import Any

import newrelic.agent


def agent_available() -> bool:
    """True when the New Relic agent is initialized (registration may still be pending)."""
    try:
        return newrelic.agent.global_settings().enabled
    except Exception:  # noqa: BLE001
        return False


def record_custom_event(event_type: str, params: dict[str, Any]) -> None:
    newrelic.agent.record_custom_event(event_type, params)


def record_custom_metric(name: str, value: float) -> None:
    newrelic.agent.record_custom_metric(f"Custom/{name}", value)


def notice_error(error: BaseException, attributes: dict[str, Any] | None = None) -> None:
    newrelic.agent.notice_error(error=(type(error), error, error.__traceback__), attributes=attributes or {})
