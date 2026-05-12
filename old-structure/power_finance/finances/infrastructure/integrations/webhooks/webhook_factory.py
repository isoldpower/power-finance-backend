from finances.application.interfaces import EventPayloadFactory
from finances.domain.entities import WebhookType

from finances.domain.events import (
    TransactionCreatedEvent,
    TransactionDeletedEvent,
    WebhookDeliveryStatusChangedEvent,
)


class WebhookPayloadFactory(EventPayloadFactory):
    def from_transaction_created(self, event: TransactionCreatedEvent) -> dict:
        return {
            "id": str(event.event_id),
            "type": WebhookType.TransactionCreate,
            "occurred_at": event.occurred_at.isoformat(),
            "data": {
                "transaction_id": str(event.transaction_id),
                "wallet_id": str(event.wallet_id),
                "amount": str(event.amount),
                "created_at": event.created_at.isoformat(),
            },
        }

    def from_transaction_deleted(self, event: TransactionDeletedEvent) -> dict:
        return {
            "id": str(event.event_id),
            "type": WebhookType.TransactionDelete,
            "occurred_at": event.occurred_at.isoformat(),
            "data": {
                "transaction_id": str(event.transaction_id),
                "wallet_id": str(event.wallet_id),
                "amount": str(event.amount),
                "cancelled_by": str(event.cancelled_by),
                "created_at": event.created_at.isoformat(),
            }
        }

    def from_delivery_status_changed(self, event: WebhookDeliveryStatusChangedEvent) -> dict:
        return {
            "event_id": str(event.event_id),
            "delivery_id": str(event.delivery_id),
            "endpoint_id": str(event.endpoint_id),
            "status": event.status,
            "event_type": "notification.delivery.status_changed",
        }