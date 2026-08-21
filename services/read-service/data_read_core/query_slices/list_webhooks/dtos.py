from dataclasses import dataclass

from data_read_core.shared.pagination import PageRequest
from data_read_core.shared.postgres_orm import WebhookReadModel
from data_read_core.shared.timestamps import to_iso


@dataclass(frozen=True)
class ListWebhooksQuery:
    user_id: int
    page: PageRequest


@dataclass(frozen=True)
class CacheOperationData:
    user_id: int
    limit: int
    cursor: str


@dataclass(frozen=True)
class WebhookDTO:
    id: str
    user_id: int
    title: str
    url: str
    is_active: bool
    created_at: str
    updated_at: str | None

    @classmethod
    def from_read_model(cls, model: WebhookReadModel) -> "WebhookDTO":
        return cls(
            id=str(model.id),
            user_id=model.user_id,
            title=model.title,
            url=model.url,
            is_active=model.is_active,
            created_at=to_iso(model.created_at),
            updated_at=to_iso(model.updated_at),
        )

    @classmethod
    def from_cache(cls, raw: dict) -> "WebhookDTO":
        return cls(
            id=raw["id"],
            user_id=raw["user_id"],
            title=raw["title"],
            url=raw["url"],
            is_active=raw["is_active"],
            created_at=raw["created_at"],
            updated_at=raw["updated_at"],
        )

    def to_cache(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "url": self.url,
            "is_active": self.is_active,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
