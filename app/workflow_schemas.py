from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


class ResponseMeta(BaseModel):
    request_id: str
    timestamp: datetime


class StandardApiResponse(BaseModel):
    status: Literal["success"] = "success"
    message: str
    data: dict[str, Any] = Field(default_factory=dict)
    meta: ResponseMeta


class FailureIngestRequest(BaseModel):
    source: str = "NEW_RELIC"
    incident: dict[str, Any] = Field(default_factory=dict)
    context: dict[str, Any] = Field(default_factory=dict)


class AgentInvokeRequest(BaseModel):
    requested_by: str
    action: str = "REMEDIATE"
    input: dict[str, Any] = Field(default_factory=dict)


class AgentResultRequest(BaseModel):
    outcome: Literal["FAILED", "SUCCEEDED"]
    validated_resolved: bool = False
    result: dict[str, Any] = Field(default_factory=dict)
    error: str = ""


def response_ok(message: str, data: dict[str, Any], request_id: str = "") -> StandardApiResponse:
    return StandardApiResponse(
        message=message,
        data=data,
        meta=ResponseMeta(
            request_id=request_id or str(uuid4()),
            timestamp=datetime.now(timezone.utc),
        ),
    )
