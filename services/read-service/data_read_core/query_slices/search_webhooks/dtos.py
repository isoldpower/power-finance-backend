from dataclasses import dataclass
from typing import Any

from data_read_core.shared.pagination import PageRequest
from data_read_core.shared.postgres_orm import WebhookReadModel
from data_read_core.shared.timestamps import to_iso


@dataclass(frozen=True)
class SearchWebhooksQuery:
    user_id: int
    filter_body: dict[str, Any]
    page: PageRequest


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
