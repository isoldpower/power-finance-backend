import pytest
from opentelemetry import context as context_api
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from observability import (
    DEMO_SESSION_BAGGAGE_ENTRY_NAME,
    BaggageSpanAttributesProcessor,
    KafkaMessageContextBinder,
    write_baggage_entry,
)


@pytest.fixture
def finished_span_exporter() -> InMemorySpanExporter:
    return InMemorySpanExporter()


@pytest.fixture
def demo_session_tracer(finished_span_exporter):
    tracer_provider = TracerProvider()
    tracer_provider.add_span_processor(
        BaggageSpanAttributesProcessor((DEMO_SESSION_BAGGAGE_ENTRY_NAME,)),
    )
    tracer_provider.add_span_processor(SimpleSpanProcessor(finished_span_exporter))

    return tracer_provider.get_tracer("baggage-span-attributes-tests")


def test_span_started_under_demo_baggage_carries_the_session_attribute(
    demo_session_tracer,
    finished_span_exporter,
):
    attachment_token = context_api.attach(
        write_baggage_entry(DEMO_SESSION_BAGGAGE_ENTRY_NAME, "portfolio-visitor-session"),
    )
    with (
        demo_session_tracer.start_as_current_span("write-request"),
        demo_session_tracer.start_as_current_span("database-insert"),
    ):
        pass
    context_api.detach(attachment_token)

    finished_spans = finished_span_exporter.get_finished_spans()

    assert len(finished_spans) == 2
    assert all(
        finished_span.attributes[DEMO_SESSION_BAGGAGE_ENTRY_NAME] == "portfolio-visitor-session"
        for finished_span in finished_spans
    )


def test_span_without_demo_baggage_carries_no_session_attribute(
    demo_session_tracer,
    finished_span_exporter,
):
    with demo_session_tracer.start_as_current_span("write-request"):
        pass

    (finished_span,) = finished_span_exporter.get_finished_spans()

    assert DEMO_SESSION_BAGGAGE_ENTRY_NAME not in finished_span.attributes


def test_consumer_span_inherits_the_session_from_kafka_baggage_header(
    demo_session_tracer,
    finished_span_exporter,
):
    message_binder = KafkaMessageContextBinder()
    attachment_token = message_binder.bind(
        [("baggage", b"sandbox-id=nikita,demo-session=portfolio-visitor-session")],
    )
    with demo_session_tracer.start_as_current_span("projection-consume"):
        pass
    message_binder.unbind(attachment_token)

    (finished_span,) = finished_span_exporter.get_finished_spans()

    assert finished_span.attributes[DEMO_SESSION_BAGGAGE_ENTRY_NAME] == "portfolio-visitor-session"
    assert "sandbox-id" not in finished_span.attributes
