from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


class NotificationService:
    def notify_human(
        self,
        *,
        incident_id: str,
        title: str,
        message: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return {
            "notification_id": str(uuid4()),
            "channel": "human",
            "incident_id": incident_id,
            "title": title,
            "message": message,
            "context": context or {},
            "delivered": True,
            "sent_at": datetime.now(timezone.utc).isoformat(),
        }


notification_service = NotificationService()
