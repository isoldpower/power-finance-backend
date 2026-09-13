from typing import NamedTuple


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
