from dataclasses import dataclass

from data_read_core.shared.postgres_orm import WebhookSubscriptionReadModel
from data_read_core.shared.timestamps import to_iso


@dataclass(frozen=True)
class ListWebhookEventsQuery:
    user_id: int
    webhook_id: str


@dataclass(frozen=True)
class WebhookSubscriptionDTO:
    id: str
    webhook_id: str
    event_type: str
    is_active: bool
    created_at: str

    @classmethod
    def from_read_model(cls, model: WebhookSubscriptionReadModel) -> "WebhookSubscriptionDTO":
        return cls(
            id=str(model.id),
            webhook_id=str(model.webhook_id),
            event_type=model.event_type,
            is_active=model.is_active,
            created_at=to_iso(model.created_at),
        )

    @classmethod
    def from_cache(cls, raw: dict) -> "WebhookSubscriptionDTO":
        return cls(
            id=raw["id"],
            webhook_id=raw["webhook_id"],
            event_type=raw["event_type"],
            is_active=raw["is_active"],
            created_at=raw["created_at"],
        )

    def to_cache(self) -> dict:
        return {
            "id": self.id,
            "webhook_id": self.webhook_id,
            "event_type": self.event_type,
            "is_active": self.is_active,
            "created_at": self.created_at,
        }
