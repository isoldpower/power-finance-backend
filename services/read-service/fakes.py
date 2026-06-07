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


class FakeConsumedMessage:
    """Stand-in for kafka_client_py.ConsumedMessage (a structural Protocol).

    Built with envelope headers as a list of ``(name, bytes)`` pairs, matching
    what the real consumer hands the OutboxEnvelopeDecoder.
    """

    def __init__(
        self,
        *,
        headers: list[tuple[str, bytes]] | None = None,
        key: bytes | None = b"agg-1",
        value: bytes | None = b"{}",
        topic: str = "events.async",
        partition: int = 0,
        offset: int = 0,
    ) -> None:
        self.headers = headers if headers is not None else []
        self.key = key
        self.value = value
        self.topic = topic
        self.partition = partition
        self.offset = offset


def make_consumed_message(
    *,
    event_id: str | None = "evt-1",
    event_type: str | None = "WalletCreated",
    aggregate_type: str | None = "wallet",
    outbox_seq: int | None = 1,
    **kwargs,
) -> FakeConsumedMessage:
    """Build a FakeConsumedMessage with the standard envelope headers set.

    A header is omitted when its value is ``None`` so tests can exercise the
    decoder's missing-header paths.
    """

    headers: list[tuple[str, bytes]] = []
    if event_id is not None:
        headers.append(("event_id", event_id.encode("utf-8")))
    if event_type is not None:
        headers.append(("event_type", event_type.encode("utf-8")))
    if aggregate_type is not None:
        headers.append(("aggregate_type", aggregate_type.encode("utf-8")))
    if outbox_seq is not None:
        headers.append(("outbox_seq", str(outbox_seq).encode("utf-8")))
    return FakeConsumedMessage(headers=headers, **kwargs)


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
