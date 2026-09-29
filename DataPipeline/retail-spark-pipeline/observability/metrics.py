"""Metric helpers for pipeline observability, backed by the New Relic Python agent."""

from __future__ import annotations

from typing import Any

from observability.newrelic_exporter import agent_available, record_custom_metric


class PipelineMetrics:
    """Records pipeline metrics as New Relic custom metrics."""

    def record_metric(self, name: str, value: float, attributes: dict[str, Any]) -> None:
        if not agent_available():
            return
        record_custom_metric(name, float(value))
