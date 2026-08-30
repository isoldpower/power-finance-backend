from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass(frozen=True, slots=True)
class OutboxEntry:
    """A row bound for the outbox table, already flattened out of its proto."""

    event_id: UUID
    event_type: str
    aggregate_type: str
    aggregate_id: str
    partition_key: str
    occurred_at: datetime
    payload: dict[str, Any]
