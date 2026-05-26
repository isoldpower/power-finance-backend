from typing import Protocol

from ..headers import KafkaHeaders


class ConsumedMessage(Protocol):
    topic: str
    partition: int
    offset: int
    key: bytes | None
    value: bytes | None
    headers: KafkaHeaders | None
