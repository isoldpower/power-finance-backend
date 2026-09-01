from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class NotificationDTO:
    id: UUID
    user_id: int
    title: str
    body: str
    payload: dict | None
    severity: str
    subject_type: str | None
    subject_id: str | None
    acknowledged_at: datetime | None
    created_at: datetime
    updated_at: datetime | None
    deleted_at: datetime | None = None
