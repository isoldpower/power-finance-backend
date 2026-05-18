"""Idempotent-consumer dedupe support.

Kafka guarantees at-least-once. To get effectively-once at the application
level, consumers must remember which `event_id`s they've already processed.
This module ships:

* `DedupeStore` — Protocol so consumers can plug in any backend (Postgres,
  Redis, in-memory for tests).
* `PostgresDedupeStore` — psycopg-async implementation backed by a single
  table per consumer group.

The recommended pattern is to call `mark()` *inside the same transaction*
that applies the message's side effects, so the dedupe row and the
projection write commit atomically. `PostgresDedupeStore.mark()` accepts an
existing connection for exactly this reason.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol

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


class DedupeStore(Protocol):
    async def seen(self, event_id: str) -> bool: ...

    async def mark(
        self,
        event_id: str,
        *,
        conn: psycopg.AsyncConnection | None = None,
        consumed_at: datetime | None = None,
    ) -> None: ...


class PostgresDedupeStore:
    """Postgres-backed dedupe store keyed by `(consumer_group, event_id)`.

    `seen()` opens its own short connection from the pool (read-only check
    before work begins). `mark()` accepts an external connection so callers
    can commit it together with their projection writes — that atomicity is
    the whole point of dedupe.
    """

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
        sql = f"SELECT 1 FROM {self._table} WHERE consumer_group = %s AND event_id = %s"
        async with self._pool.connection() as conn, conn.cursor() as cur:
            await cur.execute(sql, (self._consumer_group, event_id))
            return await cur.fetchone() is not None

    async def mark(
        self,
        event_id: str,
        *,
        conn: psycopg.AsyncConnection | None = None,
        consumed_at: datetime | None = None,
    ) -> None:
        ts = consumed_at or datetime.now(UTC)
        sql = (
            f"INSERT INTO {self._table} (consumer_group, event_id, consumed_at) "
            f"VALUES (%s, %s, %s) ON CONFLICT DO NOTHING"
        )
        params = (self._consumer_group, event_id, ts)

        if conn is not None:
            async with conn.cursor() as cur:
                await cur.execute(sql, params)
            return

        async with self._pool.connection() as owned, owned.cursor() as cur:
            await cur.execute(sql, params)


class InMemoryDedupeStore:
    """Test-only dedupe store. Not safe across processes."""

    def __init__(self) -> None:
        self._seen: set[str] = set()

    async def seen(self, event_id: str) -> bool:
        return event_id in self._seen

    async def mark(
        self,
        event_id: str,
        *,
        conn: psycopg.AsyncConnection | None = None,
        consumed_at: datetime | None = None,
    ) -> None:
        self._seen.add(event_id)
