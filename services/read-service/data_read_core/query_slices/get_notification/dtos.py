from dataclasses import dataclass
from datetime import datetime

from data_read_core.shared.postgres_orm import NotificationReadModel


@dataclass(frozen=True)
class GetNotificationQuery:
    user_id: int
    notification_id: str


@dataclass(frozen=True)
class NotificationDTO:
    id: str
    user_id: int
    short: str
    message: str
    payload: dict | None
    is_read: bool
    created_at: str

    @classmethod
    def from_read_model(cls, model: NotificationReadModel) -> "NotificationDTO":
        return cls(
            id=str(model.id),
            user_id=model.user_id,
            short=model.short,
            message=model.message,
            payload=model.payload,
            is_read=model.is_read,
            created_at=_to_iso(model.created_at),
        )

    @classmethod
    def from_cache(cls, raw: dict) -> "NotificationDTO":
        return cls(
            id=raw["id"],
            user_id=raw["user_id"],
            short=raw["short"],
            message=raw["message"],
            payload=raw["payload"],
            is_read=raw["is_read"],
            created_at=raw["created_at"],
        )

    def to_cache(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "short": self.short,
            "message": self.message,
            "payload": self.payload,
            "is_read": self.is_read,
            "created_at": self.created_at,
        }


def _to_iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None
