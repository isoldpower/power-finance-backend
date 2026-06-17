from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class NotificationDTO:
    id: UUID
    user_id: int
    short: str
    message: str
    payload: dict | None
    is_read: bool
    created_at: datetime
