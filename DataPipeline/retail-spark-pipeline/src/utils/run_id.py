"""Generates a single run_id shared by every stage of one pipeline execution."""

import secrets
from datetime import datetime, timezone


def generate_run_id(now: datetime | None = None) -> str:
    """Return a run_id like '20260925_143015_a83f21'.

    Format: <UTC timestamp YYYYMMDD_HHMMSS>_<6 hex chars>
    The same run_id must be passed explicitly into every stage
    (bronze ingestion, silver, gold, quality, pipeline logs) --
    it is intentionally not regenerated per-stage.
    """
    now = now or datetime.now(timezone.utc)
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    suffix = secrets.token_hex(3)  # 6 hex chars
    return f"{timestamp}_{suffix}"
