from collections.abc import Sequence

from opentelemetry.context import Context
from opentelemetry.sdk.trace import ReadableSpan, Span, SpanProcessor

from ..context import read_baggage_entry


class BaggageSpanAttributesProcessor(SpanProcessor):
    def __init__(self, copied_baggage_entry_names: Sequence[str]) -> None:
        self._copied_baggage_entry_names = tuple(copied_baggage_entry_names)

    def on_start(self, span: Span, parent_context: Context | None = None) -> None:
        for baggage_entry_name in self._copied_baggage_entry_names:
            baggage_entry_value = read_baggage_entry(baggage_entry_name, parent_context)
            if baggage_entry_value:
                span.set_attribute(baggage_entry_name, baggage_entry_value)

    def on_end(self, span: ReadableSpan) -> None:
        return None

    def shutdown(self) -> None:
        return None

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return True
