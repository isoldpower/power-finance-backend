from finances.application.interfaces import EventPayloadFactory
from finances.domain.events import TransactionCreatedEvent


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