import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID
from django.utils import timezone


@dataclass
class Notification:
    id: UUID
    is_read: bool
    short: str
    message: str
    user_id: int
    payload: Optional[dict]
    created_at: datetime

    @classmethod
    def create(
            cls,
            short: str,
            message: str,
            user_id: int,
            is_read: bool = False,
            payload: dict | None = None,
    ):
        return Notification(
            id=uuid.uuid4(),
            short=short,
            message=message,
            user_id=user_id,
            is_read=is_read,
            payload=payload,
            created_at=timezone.now(),
        )
