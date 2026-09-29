"""FastAPI application entrypoint."""
from __future__ import annotations

import logging

from fastapi import FastAPI

from app.api.routes import router
from app.config import get_settings

settings = get_settings()
logging.basicConfig(level=settings.log_level)

app = FastAPI(
    title=settings.app_name,
    description="Agentic backend for autonomous data-pipeline incident diagnosis.",
    version="0.1.0",
)

app.include_router(router)


@app.get("/health")
async def health() -> dict[str, str]:
    """Simple liveness check."""
    return {"status": "ok"}
