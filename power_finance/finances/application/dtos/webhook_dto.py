from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class WebhookDTO:
    id: UUID
    title: str
    subscribed_events: list[str]
    url: str
    secret: str
    created_at: datetime
    updated_at: datetime