from data_write_core.application.interfaces import OutboxRepository
from data_write_core.infrastructure.outbox_saga.outbox_events import OutboxEvent

from ..orm import OutboxEntryModel


class DjangoOutboxRepository(OutboxRepository):
    async def append(self, event: OutboxEvent) -> None:
        await OutboxEntryModel.objects.acreate(
            aggregate_type=type(event).AGGREGATE_TYPE,
            aggregate_id=event.aggregate_id,
            event_type=type(event).EVENT_TYPE,
            payload=event.to_payload(),
            occurred_at=event.occurred_at,
        )
