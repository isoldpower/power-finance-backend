from abc import abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, ClassVar
from uuid import UUID, uuid4

from data_write_core.application.interfaces import OutboxEventBase


@dataclass(frozen=True)
class OutboxEvent(OutboxEventBase):
    """Wire-contract event for the transactional outbox / Kafka stream.

    Deliberately separate from domain events: domain events are
    internal state-change signals whose shapes are driven by the
    aggregate; outbox events are the inter-service contract whose
    shapes are versioned and must remain stable for downstream
    consumers (Read Service projections, Push Service, Fraud
    consumers, …). The two pipelines are disjoint by design —
    there is no translation layer between them. Command handlers
    build outbox events directly from the work they performed.

    Subclasses declare:
    - `AGGREGATE_TYPE` (ClassVar) — routing dimension for the outbox table.
    - `EVENT_TYPE` (ClassVar) — name downstream consumers branch on.
    - `SCHEMA_VERSION` (ClassVar) — increment on any breaking payload change.
    - `aggregate_id` (property) — partition key for Kafka ordering.
    - `to_payload()` — serialised wire body."""

    AGGREGATE_TYPE: ClassVar[str]
    EVENT_TYPE: ClassVar[str]
    SCHEMA_VERSION: ClassVar[int] = 1

    event_id: UUID = field(default_factory=uuid4, init=False)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC), init=False)

    @property
    @abstractmethod
    def aggregate_id(self) -> str:
        raise NotImplementedError()

    @abstractmethod
    def to_payload(self) -> dict[str, Any]:
        raise NotImplementedError()
