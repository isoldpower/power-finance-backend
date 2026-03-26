from finances.application.interfaces import EventPayloadFactory

from finances.domain.events import (
    TransactionCreatedEvent,
    TransactionUpdatedEvent,
    TransactionDeletedEvent,
)


class WebhookPayloadFactory(EventPayloadFactory):
    def from_transaction_created(self, event: TransactionCreatedEvent) -> dict:
        return {
            "id": str(event.event_id),
            "type": "transaction.created",
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
            "type": "transaction.updated",
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
            "type": "transaction.deleted",
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
