"""run_id generation tests (no Spark/Java required, section 11)."""

import re
from datetime import datetime, timezone

from src.utils.run_id import generate_run_id


def test_run_id_matches_expected_format():
    run_id = generate_run_id()
    assert re.fullmatch(r"\d{8}_\d{6}_[0-9a-f]{6}", run_id)


def test_run_id_uses_supplied_timestamp():
    fixed = datetime(2026, 9, 25, 14, 30, 15, tzinfo=timezone.utc)
    run_id = generate_run_id(fixed)
    assert run_id.startswith("20260925_143015_")


def test_run_id_is_unique_across_calls():
    ids = {generate_run_id() for _ in range(20)}
    assert len(ids) == 20
