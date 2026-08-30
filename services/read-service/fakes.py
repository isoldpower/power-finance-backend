"""Shared test doubles for the read-service unit tests.

Kept out of conftest.py so test files import them by name rather than relying
on pytest's conftest discovery. Conftest is reserved for fixtures.

The Kafka-shaped doubles live in `kafka_consumer_py.fakes`, beside the contract
they stand in for, and are re-exported here so a test file still has one place
to import every double from.
"""

from __future__ import annotations

from kafka_consumer_py.fakes import (
    FakeConsumedMessage,
    make_consumed_message,
    make_event,
)

__all__ = [
    "FakeConsumedMessage",
    "FakeElasticsearch",
    "FakeRedis",
    "make_consumed_message",
    "make_event",
]


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


class FakeElasticsearch:
    """In-memory stand-in for the async Elasticsearch client.

    Records the parts the projection effects touch — ``index``, ``update`` and
    ``delete`` — so tests can assert the document body, target index and id.
    ``options`` returns ``self`` so the ``.options(...).delete(...)`` chain the
    delete effect uses keeps working; the kwargs are captured for assertions.
    """

    def __init__(self) -> None:
        self.indexed: list[tuple[str, str, dict]] = []
        self.updated: list[tuple[str, str, dict, bool]] = []
        self.deleted: list[tuple[str, str]] = []
        self.options_kwargs: list[dict] = []

    async def index(self, *, index: str, id: str, document: dict) -> None:
        self.indexed.append((index, id, document))

    async def update(self, *, index: str, id: str, doc: dict, doc_as_upsert: bool = False) -> None:
        self.updated.append((index, id, doc, doc_as_upsert))

    def options(self, **kwargs) -> FakeElasticsearch:
        self.options_kwargs.append(kwargs)
        return self

    async def delete(self, *, index: str, id: str) -> None:
        self.deleted.append((index, id))
