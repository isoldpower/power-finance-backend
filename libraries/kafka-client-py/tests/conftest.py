from __future__ import annotations

from dataclasses import dataclass, field

from kafka_client_py.headers import KafkaHeaders


@dataclass
class FakeMessage:
    topic: str = "events.async"
    partition: int = 0
    offset: int = 0
    key: bytes | None = b"acct-1"
    value: bytes | None = b"payload"
    headers: KafkaHeaders | None = field(default_factory=list)


@dataclass
class CapturedPublish:
    topic: str
    key: bytes | None
    value: bytes
    headers: KafkaHeaders


class FakePublisher:
    """In-memory stand-in for AsyncPublisher used in unit tests."""

    def __init__(self) -> None:
        self.published: list[CapturedPublish] = []

    async def start(self) -> None: ...
    async def stop(self) -> None: ...

    async def publish(
        self,
        topic: str,
        *,
        value: bytes,
        key: bytes | None = None,
        headers: KafkaHeaders | None = None,
    ) -> None:
        self.published.append(
            CapturedPublish(topic=topic, key=key, value=value, headers=list(headers or []))
        )
