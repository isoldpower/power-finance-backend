from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, NamedTuple
from uuid import UUID


class PropagationContext(NamedTuple):
    traceparent: str | None
    tracestate: str | None
    baggage: str | None

    @property
    def is_empty(self) -> bool:
        return not any((self.traceparent, self.tracestate, self.baggage))


EMPTY_PROPAGATION_CONTEXT = PropagationContext(
    traceparent=None,
    tracestate=None,
    baggage=None,
)


@dataclass(frozen=True, slots=True)
class OutboxEntry:
    event_id: UUID
    event_type: str
    aggregate_type: str
    aggregate_id: str
    partition_key: str
    occurred_at: datetime
    payload: dict[str, Any]
    propagation_context: PropagationContext = field(
        default=EMPTY_PROPAGATION_CONTEXT,
    )
