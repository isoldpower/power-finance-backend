from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class WebhookDTO:
    id: UUID
    user_id: int
    title: str
    url: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class WebhookWithSecretDTO(WebhookDTO):
    """Returned only on creation and secret rotation — the only moments the
    plaintext secret is shown to the client."""

    secret: str = ""


@dataclass(frozen=True)
class WebhookSubscriptionDTO:
    id: UUID
    webhook_id: UUID
    event_type: str
    is_active: bool
    created_at: datetime
