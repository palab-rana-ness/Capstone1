"""Structured logging support for pipeline telemetry.

Logs are written to stdout as JSON and forwarded to New Relic as custom
events via the New Relic Python agent (see observability/newrelic_exporter.py),
which the agent's application_logging log-forwarding config also picks up
from the standard logging module.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any

from observability.newrelic_exporter import agent_available, record_custom_event


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class StructuredEventLogger:
    """Writes structured JSON logs to stdout and mirrors them as New Relic custom events."""

    def __init__(self) -> None:
        self._logger = logging.getLogger("pipeline_observability")
        self._logger.setLevel(logging.INFO)
        self._logger.propagate = False

        if not self._logger.handlers:
            stream_handler = logging.StreamHandler(sys.stdout)
            stream_handler.setLevel(logging.INFO)
            self._logger.addHandler(stream_handler)

    def log_event(
        self,
        event_type: str,
        level: str,
        message: str,
        payload: dict[str, Any],
    ) -> None:
        record = {
            "timestamp": _utc_timestamp(),
            "event_type": event_type,
            "level": level.upper(),
            "message": message,
            **payload,
        }
        line = json.dumps(record, default=str)
        level_upper = level.upper()
        if level_upper == "ERROR":
            self._logger.error(line)
        elif level_upper == "WARNING":
            self._logger.warning(line)
        else:
            self._logger.info(line)

        if agent_available():
            record_custom_event("PipelineEvent", {**record, "message": message})
