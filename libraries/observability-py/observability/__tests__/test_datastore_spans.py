import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import SpanKind, StatusCode

from observability import trace_datastore_operation


@pytest.fixture
def finished_span_exporter(installed_tracer_provider: TracerProvider) -> InMemorySpanExporter:
    span_exporter = InMemorySpanExporter()
    installed_tracer_provider.add_span_processor(SimpleSpanProcessor(span_exporter))

    return span_exporter


def test_datastore_operation_is_a_client_span_with_database_attributes(finished_span_exporter):
    with (
        trace.get_tracer("datastore-tests").start_as_current_span("write-request"),
        trace_datastore_operation(
            database_system="immudb",
            database_name="transactions",
            operation_name="sqlExec",
        ),
    ):
        pass

    datastore_span = next(
        finished_span
        for finished_span in finished_span_exporter.get_finished_spans()
        if finished_span.name == "sqlExec"
    )

    assert datastore_span.kind is SpanKind.CLIENT
    assert dict(datastore_span.attributes) == {
        "db.system": "immudb",
        "db.name": "transactions",
        "db.operation": "sqlExec",
    }
    assert datastore_span.parent is not None


def test_failed_datastore_operation_records_an_error(finished_span_exporter):
    with (
        pytest.raises(ConnectionError),
        trace_datastore_operation(
            database_system="immudb",
            database_name="transactions",
            operation_name="verifiedSet",
        ),
    ):
        raise ConnectionError("immudb unreachable")

    (failed_span,) = [
        finished_span
        for finished_span in finished_span_exporter.get_finished_spans()
        if finished_span.name == "verifiedSet"
    ]

    assert failed_span.status.status_code is StatusCode.ERROR
