from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID

from finances.domain.events import WebhookDeliveryStatus


@dataclass
class WebhookDTO:
    id: UUID
    title: str
    url: str
    secret: str
    created_at: datetime
    updated_at: datetime


@dataclass
class WebhookDeliveryAttemptDTO:
    id: int
    delivery_id: UUID
    attempt_number: int
    request_headers: dict
    request_body: dict
    response_status: int | None
    response_body: str | None
    error_message: str | None
    started_at: datetime
    finished_at: datetime


@dataclass
class WebhookDeliveryDTO:
    id: UUID
    status: WebhookDeliveryStatus
    endpoint_id: UUID
    event_id: UUID
    updated_at: Optional[datetime]
    delivered_at: Optional[datetime]
    next_retry_at: Optional[datetime]


@dataclass
class WebhookSubscriptionDTO:
    id: UUID
    event_type: str
    endpoint_id: UUID
    is_active: bool
