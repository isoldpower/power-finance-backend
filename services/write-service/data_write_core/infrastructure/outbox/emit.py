from data_write_core.domain.events import (
    DomainEvent,
    TransactionCreatedEvent,
    TransactionDeletedEvent,
    WalletDeletedEvent,
    WalletUpdatedEvent,
    WebhookDeliveryStatusChangedEvent,
)
from data_write_core.infrastructure.orm import OutboxEntryModel

from ._serializer import event_to_payload


def _resolve_outbox_metadata(event: DomainEvent) -> tuple[str, str, str]:
    """Return (event_type, aggregate_type, aggregate_id) for a domain event.
    Centralised so new event types fail loudly until registered here."""
    if isinstance(event, TransactionCreatedEvent):
        return "TransactionCreated", "transaction", str(event.transaction_id)
    if isinstance(event, TransactionDeletedEvent):
        return "TransactionDeleted", "transaction", str(event.transaction_id)
    if isinstance(event, WalletDeletedEvent):
        return "WalletDeleted", "wallet", str(event.wallet_id)
    if isinstance(event, WalletUpdatedEvent):
        return "WalletUpdated", "wallet", str(event.wallet_id)
    if isinstance(event, WebhookDeliveryStatusChangedEvent):
        return (
            "WebhookDeliveryStatusChanged",
            "webhook_delivery",
            str(event.delivery_id),
        )
    raise ValueError(f"No outbox routing registered for event {type(event).__name__}")


async def emit_event(event: DomainEvent) -> OutboxEntryModel:
    event_type, aggregate_type, aggregate_id = _resolve_outbox_metadata(event)
    return await OutboxEntryModel.objects.acreate(
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        event_type=event_type,
        payload=event_to_payload(event),
        occurred_at=event.occurred_at,
    )
