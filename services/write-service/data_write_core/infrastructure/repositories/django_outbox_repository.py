from data_write_core.application.interfaces import OutboxEventBase, OutboxRepository

from ..orm import OutboxEntryModel


class DjangoOutboxRepository(OutboxRepository):
    async def append(self, event: OutboxEventBase) -> int:
        row = await OutboxEntryModel.objects.acreate(
            event_id=event.event_id,
            aggregate_type=type(event).AGGREGATE_TYPE,
            aggregate_id=event.aggregate_id,
            event_type=type(event).EVENT_TYPE,
            payload=event.to_payload(),
            occurred_at=event.occurred_at,
        )

        return row.id

    async def get_latest_sequence(self) -> int:
        latest_row = await OutboxEntryModel.objects.alatest("id")

        return latest_row.id
