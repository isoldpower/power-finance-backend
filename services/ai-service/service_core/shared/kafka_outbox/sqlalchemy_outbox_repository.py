from collections.abc import Sequence

from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession

from ..db_connection import OutboxEntryModel
from .contracts import OutboxEntry
from .outbox_repository import OutboxRepository


class SqlAlchemyOutboxRepository(OutboxRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def publish(self, entries: Sequence[OutboxEntry]) -> None:
        if not entries:
            return

        await self._session.execute(
            insert(OutboxEntryModel),
            [
                {
                    "event_id": entry.event_id,
                    "aggregate_type": entry.aggregate_type,
                    "aggregate_id": entry.aggregate_id,
                    "partition_key": entry.partition_key,
                    "event_type": entry.event_type,
                    "payload": entry.payload,
                    "occurred_at": entry.occurred_at,
                }
                for entry in entries
            ],
        )
