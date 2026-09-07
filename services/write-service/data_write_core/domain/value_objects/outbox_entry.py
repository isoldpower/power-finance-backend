from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass(frozen=True)
class OutboxEntry:
    event_id: UUID
    event_type: str
    aggregate_type: str
    aggregate_id: str
    partition_key: str
    occurred_at: datetime
    schema_version: int
    payload: dict[str, Any]
