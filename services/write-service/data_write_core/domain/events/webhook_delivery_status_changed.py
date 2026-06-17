from dataclasses import dataclass
from enum import Enum
from uuid import UUID

from .domain_event import DomainEvent


class WebhookDeliveryStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    RETRY_SCHEDULED = "retry_scheduled"
    IN_PROGRESS = "in_progress"


@dataclass(frozen=True)
class WebhookDeliveryStatusChangedEvent(DomainEvent):
    delivery_id: UUID
    endpoint_id: UUID
    user_id: int
    status: WebhookDeliveryStatus
