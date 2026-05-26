"""DedupeGate: the cheap pre-check that decides whether to invoke the user handler.

Four short-circuit branches, each costs nothing but is load-bearing:
1. store unconfigured → never dedupe
2. extractor unconfigured → never dedupe
3. extractor returns None (no event id on this message) → process anyway
4. store says seen → skip

Pin each so a future "be more strict" change is intentional, not accidental.
"""

from __future__ import annotations

import pytest
from kafka_client_py.consumer.dedupe.gate import DedupeGate
from kafka_client_py.consumer.dedupe.store import InMemoryDedupeStore

from tests.fakes import FakeMessage


class _SpyStore:
    """Records calls; lets the test choose the seen() result."""

    def __init__(self, seen_result: bool = False) -> None:
        self._seen_result = seen_result
        self.seen_calls: list[str] = []

    async def seen(self, event_id: str) -> bool:
        self.seen_calls.append(event_id)
        return self._seen_result

    async def mark(self, event_id: str, **_) -> None:
        pass


@pytest.mark.asyncio
async def test_returns_false_when_store_is_none():
    # Dedupe disabled at construction → never claim "already processed".
    gate = DedupeGate(dedupe_store=None, event_id_extractor=lambda m: "evt-1")

    assert await gate.already_processed(FakeMessage()) is False


@pytest.mark.asyncio
async def test_returns_false_when_extractor_is_none():
    # No way to derive an event id → can't dedupe; let the handler run.
    gate = DedupeGate(dedupe_store=InMemoryDedupeStore(), event_id_extractor=None)

    assert await gate.already_processed(FakeMessage()) is False


@pytest.mark.asyncio
async def test_does_not_call_store_when_disabled():
    # When dedupe is off, the gate must not touch the store at all —
    # this matters because the store may be expensive (DB round trip).
    store = _SpyStore(seen_result=True)
    gate = DedupeGate(dedupe_store=store, event_id_extractor=None)

    await gate.already_processed(FakeMessage())

    assert store.seen_calls == []


@pytest.mark.asyncio
async def test_returns_false_when_extractor_yields_none():
    # Message has no event id (e.g. legacy producer); process anyway
    # rather than swallow silently.
    store = _SpyStore(seen_result=True)
    gate = DedupeGate(dedupe_store=store, event_id_extractor=lambda m: None)

    assert await gate.already_processed(FakeMessage()) is False
    assert store.seen_calls == []


@pytest.mark.asyncio
async def test_returns_true_when_store_reports_seen():
    store = _SpyStore(seen_result=True)
    gate = DedupeGate(dedupe_store=store, event_id_extractor=lambda m: "evt-1")

    assert await gate.already_processed(FakeMessage()) is True
    assert store.seen_calls == ["evt-1"]


@pytest.mark.asyncio
async def test_returns_false_when_store_reports_not_seen():
    store = _SpyStore(seen_result=False)
    gate = DedupeGate(dedupe_store=store, event_id_extractor=lambda m: "evt-1")

    assert await gate.already_processed(FakeMessage()) is False
    assert store.seen_calls == ["evt-1"]


@pytest.mark.asyncio
async def test_extractor_is_called_with_the_message():
    captured: list = []

    def extractor(message):
        captured.append(message)
        return "evt-1"

    gate = DedupeGate(dedupe_store=InMemoryDedupeStore(), event_id_extractor=extractor)
    message = FakeMessage()

    await gate.already_processed(message)

    assert captured == [message]
