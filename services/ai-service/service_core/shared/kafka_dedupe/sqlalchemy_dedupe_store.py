from datetime import UTC, datetime

import psycopg
from kafka_client_py import DedupeStore
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from ..db_connection.engine import session_scope
from ..db_connection.models import KafkaConsumedEventModel


class SqlAlchemyDedupeStore(DedupeStore):
    def __init__(self, consumer_group: str) -> None:
        self._consumer_group = consumer_group

    async def seen(self, event_id: str) -> bool:
        async with session_scope() as session:
            found = await session.scalar(
                select(KafkaConsumedEventModel.event_id).where(
                    KafkaConsumedEventModel.consumer_group == self._consumer_group,
                    KafkaConsumedEventModel.event_id == event_id,
                )
            )

        return found is not None

    async def mark(
        self,
        event_id: str,
        *,
        connection: psycopg.AsyncConnection | None = None,
        consumed_at: datetime | None = None,
    ) -> None:
        statement = (
            insert(KafkaConsumedEventModel)
            .values(
                consumer_group=self._consumer_group,
                event_id=event_id,
                consumed_at=consumed_at or datetime.now(UTC),
            )
            .on_conflict_do_nothing(index_elements=["consumer_group", "event_id"])
        )

        async with session_scope() as session:
            await session.execute(statement)
