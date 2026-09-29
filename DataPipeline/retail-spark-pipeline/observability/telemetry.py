"""Telemetry facade to keep observability concerns separate from pipeline logic."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from time import perf_counter
from typing import Any

from observability.logging_config import StructuredEventLogger
from observability.metrics import PipelineMetrics
from observability.newrelic_exporter import agent_available


SENSITIVE_TOKENS = (
    "secret",
    "password",
    "token",
    "credential",
    "license_key",
    "aws_access_key",
    "aws_secret",
    "authorization",
)


@dataclass(frozen=True)
class TelemetrySettings:
    pipeline_id: str
    environment: str
    service_name: str
    service_version: str


class PipelineTelemetry:
    """Non-blocking telemetry writer for logs and metrics, backed by the New Relic agent."""

    def __init__(self, cfg: TelemetrySettings, run_id: str, tenant_id: str) -> None:
        self._cfg = cfg
        self._run_id = run_id
        self._tenant_id = tenant_id
        self._enabled = agent_available()
        self._event_logger = StructuredEventLogger()
        self._metrics = PipelineMetrics()

        if not self._enabled:
            self._event_logger.log_event(
                event_type="TELEMETRY_EXPORT_FAILURE",
                level="WARNING",
                message="New Relic agent not initialized; telemetry export disabled",
                payload={"pipeline_id": cfg.pipeline_id, "run_id": run_id, "tenant_id": tenant_id},
            )

    def _sanitize(self, payload: dict[str, Any]) -> dict[str, Any]:
        clean: dict[str, Any] = {}
        for key, value in payload.items():
            low = key.lower()
            if any(token in low for token in SENSITIVE_TOKENS):
                continue
            clean[key] = value
        return clean

    def _base_attrs(self) -> dict[str, Any]:
        return {
            "pipeline_id": self._cfg.pipeline_id,
            "run_id": self._run_id,
            "tenant_id": self._tenant_id,
            "environment": self._cfg.environment,
            "service_name": self._cfg.service_name,
        }

    def log_event(self, event_type: str, level: str, message: str, **attributes: Any) -> None:
        payload = self._sanitize({**self._base_attrs(), **attributes})
        try:
            self._event_logger.log_event(event_type=event_type, level=level, message=message, payload=payload)
        except Exception as exc:  # noqa: BLE001
            self._event_logger.log_event(
                event_type="TELEMETRY_EXPORT_FAILURE",
                level="WARNING",
                message="Failed to emit telemetry log event",
                payload={**self._base_attrs(), "error": str(exc), "failed_event_type": event_type},
            )

    def record_metric(self, name: str, value: float, **attributes: Any) -> None:
        if not self._enabled:
            return
        payload = self._sanitize({**self._base_attrs(), **attributes})
        try:
            self._metrics.record_metric(name, value, payload)
        except Exception as exc:  # noqa: BLE001
            self.log_event(
                "TELEMETRY_EXPORT_FAILURE",
                "WARNING",
                "Failed to emit telemetry metric",
                metric_name=name,
                metric_value=value,
                error=str(exc),
            )

    def stage_timer(self) -> float:
        return perf_counter()

    def stage_elapsed(self, start: float) -> float:
        return round(perf_counter() - start, 4)

    def timestamp(self) -> str:
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    def shutdown(self) -> None:
        """No-op: the New Relic agent's lifecycle is managed by run_pipeline.py."""
        return


def build_telemetry(settings: Any, run_id: str, tenant_id: str) -> PipelineTelemetry:
    cfg = TelemetrySettings(
        pipeline_id=settings.pipeline_id,
        environment=settings.environment,
        service_name=settings.new_relic_service_name,
        service_version=settings.service_version,
    )
    return PipelineTelemetry(cfg, run_id=run_id, tenant_id=tenant_id)
