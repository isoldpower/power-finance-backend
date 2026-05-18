from dataclasses import dataclass
from typing import Any, ClassVar
from uuid import UUID

from data_write_core.domain.events import WebhookDeliveryStatus

from ._outbox_event import OutboxEvent


@dataclass(frozen=True)
class WebhookDeliveryStatusChangedOutboxEvent(OutboxEvent):
    AGGREGATE_TYPE: ClassVar[str] = "webhook_delivery"
    EVENT_TYPE: ClassVar[str] = "WebhookDeliveryStatusChanged"
    SCHEMA_VERSION: ClassVar[int] = 1

    delivery_id: UUID
    endpoint_id: UUID
    user_id: int
    status: WebhookDeliveryStatus

    @property
    def aggregate_id(self) -> str:
        return str(self.delivery_id)

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "event_id": str(self.event_id),
            "occurred_at": self.occurred_at.isoformat(),
            "delivery_id": str(self.delivery_id),
            "endpoint_id": str(self.endpoint_id),
            "user_id": self.user_id,
            "status": self.status.value,
        }
