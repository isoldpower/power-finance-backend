from abc import ABC, abstractmethod
from datetime import UTC, datetime

import psycopg
from psycopg_pool import AsyncConnectionPool

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS kafka_consumed_events (
    consumer_group TEXT NOT NULL,
    event_id       TEXT NOT NULL,
    consumed_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (consumer_group, event_id)
);

CREATE INDEX IF NOT EXISTS kafka_consumed_events_consumed_at_idx
    ON kafka_consumed_events (consumed_at);
"""


class DedupeStore(ABC):
    @abstractmethod
    async def seen(self, event_id: str) -> bool:
        raise NotImplementedError()

    @abstractmethod
    async def mark(
        self,
        event_id: str,
        *,
        connection: psycopg.AsyncConnection | None = None,
        consumed_at: datetime | None = None,
    ) -> None:
        raise NotImplementedError()


class PostgresDedupeStore(DedupeStore):
    def __init__(
        self,
        pool: AsyncConnectionPool,
        consumer_group: str,
        *,
        table: str = "kafka_consumed_events",
    ) -> None:
        self._pool = pool
        self._consumer_group = consumer_group
        self._table = table

    async def seen(self, event_id: str) -> bool:
        select_statement = (
            f"SELECT 1 FROM {self._table} " f"WHERE consumer_group = %s AND event_id = %s"
        )
        async with self._pool.connection() as connection, connection.cursor() as cursor:
            await cursor.execute(
                select_statement,
                (self._consumer_group, event_id),
            )
            return await cursor.fetchone() is not None

    async def mark(
        self,
        event_id: str,
        *,
        connection: psycopg.AsyncConnection | None = None,
        consumed_at: datetime | None = None,
    ) -> None:
        consumed_at_timestamp = consumed_at or datetime.now(UTC)
        insert_statement = (
            f"INSERT INTO {self._table} (consumer_group, event_id, consumed_at) "
            f"VALUES (%s, %s, %s) ON CONFLICT DO NOTHING"
        )
        insert_parameters = (self._consumer_group, event_id, consumed_at_timestamp)

        if connection is not None:
            async with connection.cursor() as cursor:
                await cursor.execute(insert_statement, insert_parameters)
            return

        async with self._pool.connection() as owned_connection, owned_connection.cursor() as cursor:
            await cursor.execute(insert_statement, insert_parameters)


class InMemoryDedupeStore:
    def __init__(self) -> None:
        self._seen_event_ids: set[str] = set()

    async def seen(self, event_id: str) -> bool:
        return event_id in self._seen_event_ids

    async def mark(
        self,
        event_id: str,
        *,
        connection: psycopg.AsyncConnection | None = None,
        consumed_at: datetime | None = None,
    ) -> None:
        self._seen_event_ids.add(event_id)
