from google.protobuf.json_format import MessageToJson
from google.protobuf.message import Message

from .types import EventMessage


class FakeConsumedMessage:
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
    return EventMessage(
        event_id="evt-1",
        event_type=type(payload).__name__,
        aggregate_type="test-aggregate",
        partition_key="agg-1",
        outbox_seq=outbox_seq,
        payload=MessageToJson(payload).encode("utf-8"),
        headers={},
        topic="events.async",
        partition=0,
        offset=0,
    )
