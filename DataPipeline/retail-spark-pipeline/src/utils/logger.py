"""Simple structured console logger for the pipeline (stdout only).

Not intended as a general-purpose logging framework -- this MVP keeps
observability simple: console output for humans, JSON records written to
S3 (logs/ingestion, logs/quality, logs/pipeline) for machine consumption.
"""

import logging
import sys


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        )
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
    return logger
