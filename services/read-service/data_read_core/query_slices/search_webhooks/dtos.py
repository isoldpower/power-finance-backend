from dataclasses import dataclass
from datetime import datetime
from typing import Any

from data_read_core.shared.postgres_orm import WebhookReadModel


@dataclass(frozen=True)
class SearchWebhooksQuery:
    user_id: int
    filter_body: dict[str, Any]
    limit: int
    offset: int


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
            created_at=_to_iso(model.created_at),
            updated_at=_to_iso(model.updated_at),
        )


def _to_iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None
