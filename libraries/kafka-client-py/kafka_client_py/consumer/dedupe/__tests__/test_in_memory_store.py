"""InMemoryDedupeStore: trivial set-backed implementation for tests / local use.

Pin the contract the gate relies on: seen(x) returns False until mark(x)
has been awaited, then True forever. mark() is idempotent and tolerates
the connection/consumed_at kwargs that PostgresDedupeStore needs (so
both impls are drop-in replaceable in tests).
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from kafka_client_py.consumer.dedupe.store import InMemoryDedupeStore


@pytest.mark.asyncio
async def test_seen_returns_false_for_unmarked_event():
    store = InMemoryDedupeStore()

    assert await store.seen("evt-1") is False


@pytest.mark.asyncio
async def test_mark_then_seen_returns_true():
    store = InMemoryDedupeStore()

    await store.mark("evt-1")

    assert await store.seen("evt-1") is True


@pytest.mark.asyncio
async def test_mark_is_idempotent():
    # Marking the same event twice must not raise — the at-least-once
    # delivery model means we'll legitimately see this in production.
    store = InMemoryDedupeStore()

    await store.mark("evt-1")
    await store.mark("evt-1")

    assert await store.seen("evt-1") is True


@pytest.mark.asyncio
async def test_different_events_are_isolated():
    store = InMemoryDedupeStore()

    await store.mark("evt-1")

    assert await store.seen("evt-1") is True
    assert await store.seen("evt-2") is False


@pytest.mark.asyncio
async def test_mark_accepts_connection_kwarg_for_interface_parity():
    # The Postgres impl takes a `connection` kwarg so callers can attach
    # the dedupe write to an existing transaction. The in-memory impl
    # must accept-and-ignore it to keep test wiring identical.
    store = InMemoryDedupeStore()

    await store.mark("evt-1", connection=None)

    assert await store.seen("evt-1") is True


@pytest.mark.asyncio
async def test_mark_accepts_consumed_at_kwarg_for_interface_parity():
    store = InMemoryDedupeStore()

    await store.mark("evt-1", consumed_at=datetime(2026, 1, 1, tzinfo=UTC))

    assert await store.seen("evt-1") is True


@pytest.mark.asyncio
async def test_fresh_store_has_no_seen_events():
    store = InMemoryDedupeStore()

    assert await store.seen("anything") is False
    assert await store.seen("") is False


@pytest.mark.asyncio
async def test_two_stores_do_not_share_state():
    a = InMemoryDedupeStore()
    b = InMemoryDedupeStore()

    await a.mark("evt-1")

    assert await b.seen("evt-1") is False
