from __future__ import annotations

import grpc
from django.test import SimpleTestCase
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from data_write_core.infrastructure.immudb.resilient_client import ResilientImmudbClient


class ExpiredTokenError(grpc.RpcError):
    def code(self) -> grpc.StatusCode:
        return grpc.StatusCode.PERMISSION_DENIED

    def details(self) -> str:
        return "token has expired"


class RecordingImmudbClient:
    def __init__(self, failures_before_success: int = 0) -> None:
        self.remaining_failures = failures_before_success
        self.login_count = 0

    def sqlExec(self, statement: str) -> str:
        if self.remaining_failures > 0:
            self.remaining_failures -= 1
            raise ExpiredTokenError()
        return "executed"

    def login(self, username: str, password: str) -> None:
        self.login_count += 1

    def useDatabase(self, database: bytes) -> None:
        return None


def build_resilient_client(immudb_client: RecordingImmudbClient) -> ResilientImmudbClient:
    return ResilientImmudbClient(
        client=immudb_client,
        username="immudb",
        password="immudb",
        database="transactions",
    )


class ResilientImmudbClientTracingTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        if not isinstance(trace.get_tracer_provider(), TracerProvider):
            trace.set_tracer_provider(TracerProvider())
        cls.finished_span_exporter = InMemorySpanExporter()
        trace.get_tracer_provider().add_span_processor(
            SimpleSpanProcessor(cls.finished_span_exporter)
        )

    def setUp(self) -> None:
        self.finished_span_exporter.clear()

    def immudb_spans(self):
        return [
            finished_span
            for finished_span in self.finished_span_exporter.get_finished_spans()
            if finished_span.attributes.get("db.system") == "immudb"
        ]

    def test_each_immudb_call_is_traced_as_a_client_span(self) -> None:
        result = build_resilient_client(RecordingImmudbClient()).sqlExec("INSERT INTO money_flows")

        (immudb_span,) = self.immudb_spans()
        self.assertEqual(result, "executed")
        self.assertEqual(immudb_span.name, "sqlExec")
        self.assertEqual(immudb_span.attributes["db.name"], "transactions")
        self.assertEqual(immudb_span.attributes["db.operation"], "sqlExec")

    def test_relogin_retry_stays_inside_one_span(self) -> None:
        immudb_client = RecordingImmudbClient(failures_before_success=1)

        result = build_resilient_client(immudb_client).sqlExec("INSERT INTO money_flows")

        self.assertEqual(result, "executed")
        self.assertEqual(immudb_client.login_count, 1)
        self.assertEqual(len(self.immudb_spans()), 1)
