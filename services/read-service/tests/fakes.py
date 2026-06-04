"""Shared test doubles for the read-service unit tests.

Kept out of conftest.py so test files import them by name rather than relying
on pytest's conftest discovery. Conftest is reserved for fixtures.
"""

from __future__ import annotations

from data_read_core.shared.kafka_updates import EventMessage
from google.protobuf.json_format import MessageToJson
from google.protobuf.message import Message


class FakeRedis:
    """In-memory stand-in for the async Redis client.

    Mirrors the parts the cache code touches. Values are stored as ``str`` to
    match the real client's ``decode_responses=True`` behaviour. Records every
    ``set`` so tests can assert key, payload and TTL.
    """

    def __init__(self, store: dict[str, str] | None = None) -> None:
        self.store: dict[str, str] = dict(store or {})
        self.set_calls: list[tuple[str, str, int | None]] = []

    async def get(self, key: str) -> str | None:
        return self.store.get(key)

    async def set(self, key: str, value: str, ex: int | None = None) -> None:
        self.store[key] = value
        self.set_calls.append((key, value, ex))

    async def incr(self, key: str) -> int:
        current = int(self.store.get(key, 0)) + 1
        self.store[key] = str(current)
        return current

    async def delete(self, key: str) -> int:
        existed = key in self.store
        self.store.pop(key, None)
        return 1 if existed else 0


def make_event(payload: Message, *, outbox_seq: int | None = 1) -> EventMessage:
    """Wrap a proto message in an EventMessage the way the consumer would.

    The payload is JSON-encoded because ``decode_payload`` parses with
    ``json_format.Parse`` (the outbox stores canonical-JSON proto bodies).
    """

    return EventMessage(
        event_id="evt-1",
        event_type=type(payload).__name__,
        aggregate_type="test-aggregate",
        aggregate_id="agg-1",
        outbox_seq=outbox_seq,
        payload=MessageToJson(payload).encode("utf-8"),
        headers={},
        topic="events.async",
        partition=0,
        offset=0,
    )
