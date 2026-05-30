from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from kafka_client_py import ConsumedMessage


@dataclass(frozen=True, slots=True)
class EventMessage:
    """Decoded Kafka message exposed to handlers.

    `payload` is left as raw bytes; each handler deserializes into the proto type
    it owns. The consumer stays ignorant of business schemas.
    """

    event_id: str
    event_type: str
    aggregate_type: str
    aggregate_id: str
    outbox_seq: int | None
    payload: bytes
    headers: dict[str, bytes]
    topic: str
    partition: int
    offset: int


AsyncHandler = Callable[[EventMessage], Awaitable[None]]


class Handler(Protocol):
    async def __call__(self, event: EventMessage) -> None: ...


@runtime_checkable
class EnvelopeDecoder(Protocol):
    def decode(self, message: ConsumedMessage) -> EventMessage: ...

    def extract_event_id(self, message: ConsumedMessage) -> str | None: ...


@runtime_checkable
class ConsumerLoop(Protocol):
    async def run(self) -> None: ...


@runtime_checkable
class EventRouter(Protocol):
    def register(self, event_type: str, handler: Handler) -> None: ...

    def has(self, event_type: str) -> bool: ...

    async def dispatch(self, event: EventMessage) -> None: ...

    def registered_event_types(self) -> list[str]: ...


@runtime_checkable
class ShutdownSignal(Protocol):
    def is_stop_requested(self) -> bool: ...

    def request_stop(self) -> None: ...

    def install(self) -> None: ...
