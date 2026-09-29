#!/usr/bin/env python
"""CLI entry point.

Usage:
    python run_pipeline.py --tenant-id tenant_001 --mode full
    python run_pipeline.py --tenant-id all --mode incremental --updated-since 2026-09-24T00:00:00Z
"""

import sys
from pathlib import Path
import newrelic.agent

newrelic.agent.initialize("newrelic.ini")
newrelic.agent.register_application(timeout=10)
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.main import main  # noqa: E402

if __name__ == "__main__":
    exit_code = main()
    newrelic.agent.shutdown_agent(timeout=10)
    sys.exit(exit_code)
