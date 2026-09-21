"""The trace context an outbox row carries, captured where the row is built."""

import pytest
from kafka_messages import AccountUpdated
from observability import attach_sandbox_id, detach_sandbox_id
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider

from service_core.shared.kafka_outbox import build_outbox_entry


@pytest.fixture(scope="module")
def tracer() -> trace.Tracer:
    trace.set_tracer_provider(TracerProvider())

    return trace.get_tracer("ai-service-tests")


def _build_account_updated_entry():
    return build_outbox_entry(
        AccountUpdated(account_id="a-1", user_id=1),
        aggregate_type="account",
        aggregate_id="a-1",
        partition_key="clerk-1",
    )


def test_entry_carries_no_propagation_context_outside_a_span():
    assert _build_account_updated_entry().propagation_context.is_empty


def test_entry_carries_the_traceparent_of_the_producing_span(tracer):
    with tracer.start_as_current_span("dispatch-postings") as producing_span:
        entry = _build_account_updated_entry()
        expected_trace_id = trace.format_trace_id(producing_span.get_span_context().trace_id)

    assert entry.propagation_context.traceparent is not None
    assert expected_trace_id in entry.propagation_context.traceparent


def test_entry_carries_the_sandbox_id_as_baggage(tracer):
    with tracer.start_as_current_span("dispatch-postings"):
        attachment_token = attach_sandbox_id("nikita")
        entry = _build_account_updated_entry()
        detach_sandbox_id(attachment_token)

    assert entry.propagation_context.baggage == "sandbox-id=nikita"


def test_baseline_entry_carries_no_sandbox_baggage(tracer):
    with tracer.start_as_current_span("dispatch-postings"):
        entry = _build_account_updated_entry()

    assert entry.propagation_context.baggage is None
