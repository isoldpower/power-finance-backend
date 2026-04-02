from dataclasses import dataclass
from enum import Enum
from uuid import UUID

from .domain_event import DomainEvent


class WebhookDeliveryStatus(str, Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    RETRY = "RETRY"


@dataclass(frozen=True)
class WebhookDeliveryStatusChangedEvent(DomainEvent):
    delivery_id: UUID
    endpoint_id: UUID
    user_id: int
    status: WebhookDeliveryStatus
    attempt_number: int
