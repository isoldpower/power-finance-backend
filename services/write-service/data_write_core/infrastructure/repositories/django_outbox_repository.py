from data_write_core.application.interfaces import OutboxRepository
from data_write_core.domain.value_objects import OutboxEntry

from ..orm import OutboxEntryModel


class DjangoOutboxRepository(OutboxRepository):
    async def append(self, entry: OutboxEntry) -> int:
        row = await OutboxEntryModel.objects.acreate(
            event_id=entry.event_id,
            aggregate_type=entry.aggregate_type,
            aggregate_id=entry.aggregate_id,
            partition_key=entry.partition_key,
            event_type=entry.event_type,
            payload=entry.payload,
            occurred_at=entry.occurred_at,
        )
        return row.id

    async def get_latest_sequence(self) -> int:
        latest_row = await OutboxEntryModel.objects.alatest("id")
        return latest_row.id
