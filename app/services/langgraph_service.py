from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


class LangGraphService:
    def invoke(
        self,
        *,
        incident_id: str,
        requested_by: str,
        action: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "invocation_id": str(uuid4()),
            "incident_id": incident_id,
            "requested_by": requested_by,
            "action": action,
            "payload": payload,
            "status": "TRIGGERED",
            "triggered_at": datetime.now(timezone.utc).isoformat(),
        }


langgraph_service = LangGraphService()
