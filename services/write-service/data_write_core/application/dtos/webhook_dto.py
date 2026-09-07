from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class WebhookDTO:
    id: UUID
    user_id: int
    title: str
    url: str
    enabled: bool
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class WebhookWithSecretDTO(WebhookDTO):
    secret: str = ""


@dataclass(frozen=True)
class WebhookSubscriptionDTO:
    id: UUID
    webhook_id: UUID
    event_type: str
    created_at: datetime
