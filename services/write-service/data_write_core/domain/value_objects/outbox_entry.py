from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass(frozen=True)
class OutboxEntry:
    """Transport-agnostic outbox row. Built once by application code, written verbatim by the repository."""

    event_id: UUID
    event_type: str
    aggregate_type: str
    aggregate_id: str
    occurred_at: datetime
    schema_version: int
    payload: dict[str, Any]
