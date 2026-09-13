from observability import capture_outbox_trace_context

from .contracts import PropagationContext


def capture_propagation_context() -> PropagationContext:
    captured_trace_context = capture_outbox_trace_context()

    return PropagationContext(
        traceparent=captured_trace_context.traceparent,
        tracestate=captured_trace_context.tracestate,
        baggage=captured_trace_context.baggage,
    )
