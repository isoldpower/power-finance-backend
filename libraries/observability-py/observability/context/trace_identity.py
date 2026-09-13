from opentelemetry import trace

INVALID_TRACE_ID = 0
INVALID_SPAN_ID = 0


def current_trace_id_hex() -> str | None:
    span_context = trace.get_current_span().get_span_context()
    if span_context.trace_id == INVALID_TRACE_ID:
        return None

    return trace.format_trace_id(span_context.trace_id)


def current_span_id_hex() -> str | None:
    span_context = trace.get_current_span().get_span_context()
    if span_context.span_id == INVALID_SPAN_ID:
        return None

    return trace.format_span_id(span_context.span_id)
