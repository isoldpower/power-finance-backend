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
