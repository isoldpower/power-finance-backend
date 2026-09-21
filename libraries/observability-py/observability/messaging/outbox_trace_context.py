from typing import NamedTuple

from ..context import inject_current_context

TRACEPARENT_CARRIER_KEY = "traceparent"
TRACESTATE_CARRIER_KEY = "tracestate"
BAGGAGE_CARRIER_KEY = "baggage"


class OutboxTraceContext(NamedTuple):
    traceparent: str | None
    tracestate: str | None
    baggage: str | None

    @property
    def is_empty(self) -> bool:
        return not any((self.traceparent, self.tracestate, self.baggage))


EMPTY_OUTBOX_TRACE_CONTEXT = OutboxTraceContext(
    traceparent=None,
    tracestate=None,
    baggage=None,
)


def capture_outbox_trace_context() -> OutboxTraceContext:
    carrier = inject_current_context()

    return OutboxTraceContext(
        traceparent=carrier.get(TRACEPARENT_CARRIER_KEY),
        tracestate=carrier.get(TRACESTATE_CARRIER_KEY),
        baggage=carrier.get(BAGGAGE_CARRIER_KEY),
    )
