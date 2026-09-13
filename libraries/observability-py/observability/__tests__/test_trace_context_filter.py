"""The log filter stamps trace, span and sandbox onto every record."""

import logging

from observability import TraceContextFilter, attach_sandbox_id, detach_sandbox_id
from observability.logging.trace_context_filter import MISSING_VALUE_PLACEHOLDER


def _make_log_record() -> logging.LogRecord:
    return logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="message",
        args=(),
        exc_info=None,
    )


def test_placeholders_apply_outside_a_span():
    record = _make_log_record()

    assert TraceContextFilter().filter(record)
    assert record.trace_id == MISSING_VALUE_PLACEHOLDER
    assert record.span_id == MISSING_VALUE_PLACEHOLDER
    assert record.sandbox_id == MISSING_VALUE_PLACEHOLDER


def test_trace_and_sandbox_are_stamped_inside_a_span(tracer):
    record = _make_log_record()

    with tracer.start_as_current_span("request"):
        attachment_token = attach_sandbox_id("nikita")
        TraceContextFilter().filter(record)
        detach_sandbox_id(attachment_token)

    assert record.trace_id != MISSING_VALUE_PLACEHOLDER
    assert record.span_id != MISSING_VALUE_PLACEHOLDER
    assert record.sandbox_id == "nikita"
