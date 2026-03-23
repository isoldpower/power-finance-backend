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


@dataclass
class WebhookDeliveryAttemptDTO:
    id: int
    delivery_id: UUID
    attempt_number: int
    request_headers: dict
    request_body: dict
    response_status: int
    response_body: str
    error_message: str
    started_at: datetime
    finished_at: datetime


@dataclass
class WebhookDeliveryDTO:
    id: UUID
    status: str
    endpoint_id: UUID
    event_id: UUID
    event_type: str
    updated_at: datetime
    delivered_at: datetime
    next_retry_at: datetime