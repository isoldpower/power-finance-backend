from collections.abc import Iterator
from contextlib import contextmanager

from opentelemetry import trace
from opentelemetry.trace import SpanKind

DATASTORE_TRACER_NAME = "observability.datastore"
DATABASE_SYSTEM_ATTRIBUTE = "db.system"
DATABASE_NAME_ATTRIBUTE = "db.name"
DATABASE_OPERATION_ATTRIBUTE = "db.operation"


@contextmanager
def trace_datastore_operation(
    *,
    database_system: str,
    database_name: str,
    operation_name: str,
) -> Iterator[None]:
    with trace.get_tracer(DATASTORE_TRACER_NAME).start_as_current_span(
        operation_name,
        kind=SpanKind.CLIENT,
        attributes={
            DATABASE_SYSTEM_ATTRIBUTE: database_system,
            DATABASE_NAME_ATTRIBUTE: database_name,
            DATABASE_OPERATION_ATTRIBUTE: operation_name,
        },
    ):
        yield
