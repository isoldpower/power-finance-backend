from collections.abc import Sequence

from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession

from ..db_connection import OutboxEntryModel
from .config import OutboxColumn
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
                    OutboxColumn.EVENT_ID: entry.event_id,
                    OutboxColumn.AGGREGATE_TYPE: entry.aggregate_type,
                    OutboxColumn.AGGREGATE_ID: entry.aggregate_id,
                    OutboxColumn.PARTITION_KEY: entry.partition_key,
                    OutboxColumn.EVENT_TYPE: entry.event_type,
                    OutboxColumn.PAYLOAD: entry.payload,
                    OutboxColumn.OCCURRED_AT: entry.occurred_at,
                }
                for entry in entries
            ],
        )
