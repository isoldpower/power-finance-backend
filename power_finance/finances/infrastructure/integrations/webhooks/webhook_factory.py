from finances.application.interfaces import EventPayloadFactory
from finances.domain.entities import WebhookType

from finances.domain.events import (
    TransactionCreatedEvent,
    TransactionUpdatedEvent,
    TransactionDeletedEvent, WebhookDeliveryStatusChangedEvent,
)


class WebhookPayloadFactory(EventPayloadFactory):
    def from_transaction_created(self, event: TransactionCreatedEvent) -> dict:
        return {
            "id": str(event.event_id),
            "type": WebhookType.TransactionCreate,
            "occurred_at": event.occurred_at.isoformat(),
            "data": {
                "description": event.description,
                "transaction_id": str(event.transaction_id),
                "sender": {
                    "amount": str(event.sender.amount),
                    "currency": str(event.sender.currency_code)
                } if event.sender else None,
                "receiver": {
                    "amount": str(event.receiver.amount),
                    "currency": str(event.receiver.currency_code)
                } if event.receiver else None,
            },
        }

    def from_transaction_updated(self, event: TransactionUpdatedEvent) -> dict:
        def get_transaction_state(transaction_state):
            return {
                "sender": {
                    "amount": str(transaction_state.sender.amount),
                    "currency": str(transaction_state.sender.currency_code)
                } if transaction_state.sender else None,
                "receiver": {
                    "amount": str(transaction_state.receiver.amount),
                    "currency": str(transaction_state.receiver.currency_code)
                } if transaction_state.receiver else None,
                "description": transaction_state.description,
                "category": transaction_state.category,
            }

        return {
            "id": str(event.event_id),
            "type": WebhookType.TransactionUpdate,
            "occurred_at": event.occurred_at.isoformat(),
            "data": {
                "previous_data": get_transaction_state(event.old_transaction),
                "current_data": get_transaction_state(event.current_transaction),
                "transaction_id": event.transaction_id,
                "updated_at": event.updated_at.isoformat(),
            }
        }

    def from_transaction_deleted(self, event: TransactionDeletedEvent) -> dict:
        return {
            "id": str(event.event_id),
            "type": WebhookType.TransactionDelete,
            "occurred_at": event.occurred_at.isoformat(),
            "data": {
                "description": event.description,
                "transaction_id": str(event.transaction_id),
                "sender": {
                    "amount": str(event.sender.amount),
                    "currency": str(event.sender.currency_code)
                } if event.sender else None,
                "receiver": {
                    "amount": str(event.receiver.amount),
                    "currency": str(event.receiver.currency_code)
                } if event.receiver else None,
            }
        }

    def from_delivery_status_changed(self, event: WebhookDeliveryStatusChangedEvent) -> dict:
        return {
            "event_id": str(event.event_id),
            "delivery_id": str(event.delivery_id),
            "endpoint_id": str(event.endpoint_id),
            "status": event.status,
            "event_type": "notification.delivery.status_changed",
            "attempt_number": event.attempt_number,
        }