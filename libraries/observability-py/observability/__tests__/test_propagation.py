"""Trace context and baggage survive the hop through Kafka headers."""

from observability import (
    KafkaMessageContextBinder,
    attach_sandbox_id,
    capture_outbox_trace_context,
    current_trace_id_hex,
    detach_sandbox_id,
)


def _to_kafka_headers(outbox_trace_context) -> list[tuple[str, bytes]]:
    return [
        (header_name, header_value.encode("utf-8"))
        for header_name, header_value in (
            ("traceparent", outbox_trace_context.traceparent),
            ("tracestate", outbox_trace_context.tracestate),
            ("baggage", outbox_trace_context.baggage),
        )
        if header_value is not None
    ]


def test_capture_is_empty_without_an_active_span():
    assert capture_outbox_trace_context().is_empty


def test_capture_carries_traceparent_of_the_active_span(tracer):
    with tracer.start_as_current_span("write-request"):
        captured = capture_outbox_trace_context()
        active_trace_id = current_trace_id_hex()

    assert captured.traceparent is not None
    assert active_trace_id is not None
    assert active_trace_id in captured.traceparent


def test_capture_carries_sandbox_id_as_baggage(tracer):
    with tracer.start_as_current_span("write-request"):
        attachment_token = attach_sandbox_id("nikita")
        captured = capture_outbox_trace_context()
        detach_sandbox_id(attachment_token)

    assert captured.baggage == "sandbox-id=nikita"


def test_consumer_rejoins_the_producer_trace(tracer):
    with tracer.start_as_current_span("write-request"):
        captured = capture_outbox_trace_context()
        producer_trace_id = current_trace_id_hex()

    binder = KafkaMessageContextBinder()
    attachment_token = binder.bind(_to_kafka_headers(captured))
    with tracer.start_as_current_span("consumer-work"):
        consumer_trace_id = current_trace_id_hex()
    binder.unbind(attachment_token)

    assert consumer_trace_id == producer_trace_id


def test_binder_reads_sandbox_id_without_attaching_context(tracer):
    with tracer.start_as_current_span("write-request"):
        attachment_token = attach_sandbox_id("nikita")
        captured = capture_outbox_trace_context()
        detach_sandbox_id(attachment_token)

    binder = KafkaMessageContextBinder()

    assert binder.read_sandbox_id(_to_kafka_headers(captured)) == "nikita"


def test_binder_reads_no_sandbox_id_from_baseline_headers(tracer):
    with tracer.start_as_current_span("write-request"):
        captured = capture_outbox_trace_context()

    binder = KafkaMessageContextBinder()

    assert binder.read_sandbox_id(_to_kafka_headers(captured)) is None


def test_binder_tolerates_missing_and_undecodable_headers():
    binder = KafkaMessageContextBinder()

    assert binder.read_sandbox_id(()) is None
    assert binder.read_sandbox_id([("baggage", b"\xff\xfe")]) is None
