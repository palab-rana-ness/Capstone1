"""Send a minimal telemetry event + metric to New Relic for connectivity checks.

This does not touch FastAPI or S3, so it can validate observability in isolation.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import newrelic.agent

newrelic.agent.initialize(str(PROJECT_ROOT / "newrelic.ini"))
newrelic.agent.register_application(timeout=10)

from observability.telemetry import build_telemetry


def main() -> int:
    load_dotenv()

    settings = SimpleNamespace(
        pipeline_id=os.getenv("PIPELINE_ID", "retail_data_pipeline"),
        environment=os.getenv("ENVIRONMENT", "dev"),
        new_relic_service_name=os.getenv("NEW_RELIC_SERVICE_NAME", "retail-spark-pipeline"),
        service_version=os.getenv("SERVICE_VERSION", "1.0.0"),
    )

    run_id = datetime.now(timezone.utc).strftime("smoke_%Y%m%d_%H%M%S")
    telemetry = build_telemetry(settings, run_id=run_id, tenant_id="tenant_001")

    telemetry.log_event(
        "PIPELINE_START",
        "INFO",
        "Telemetry smoke test start",
        stage="pipeline",
        dataset="pipeline",
        status="RUNNING",
        smoke_test=True,
    )
    telemetry.record_metric(
        "pipeline_run_count",
        1,
        stage="pipeline",
        dataset="pipeline",
        smoke_test=True,
    )
    telemetry.log_event(
        "PIPELINE_END",
        "INFO",
        "Telemetry smoke test complete",
        stage="pipeline",
        dataset="pipeline",
        status="SUCCESS",
        smoke_test=True,
    )

    telemetry.shutdown()
    newrelic.agent.shutdown_agent(timeout=10)
    print(f"SMOKE_TELEMETRY_SENT run_id={run_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
