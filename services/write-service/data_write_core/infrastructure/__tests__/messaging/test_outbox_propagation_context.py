from __future__ import annotations

from django.test import SimpleTestCase
from kafka_messages import WalletCreated
from observability import attach_sandbox_id, detach_sandbox_id
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider

from data_write_core.infrastructure.messaging.proto import build_outbox_entry


def _build_wallet_created_entry():
    return build_outbox_entry(
        WalletCreated(wallet_id="w-1", user_id=1, title="Cash", currency_code="USD"),
        aggregate_type="wallet",
        aggregate_id="w-1",
        partition_key="clerk-1",
    )


class OutboxPropagationContextTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        trace.set_tracer_provider(TracerProvider())
        cls.tracer = trace.get_tracer("write-service-tests")

    def test_entry_carries_no_propagation_context_outside_a_span(self) -> None:
        entry = _build_wallet_created_entry()

        self.assertTrue(entry.propagation_context.is_empty)

    def test_entry_carries_the_traceparent_of_the_producing_span(self) -> None:
        with self.tracer.start_as_current_span("create-wallet") as producing_span:
            entry = _build_wallet_created_entry()
            expected_trace_id = trace.format_trace_id(
                producing_span.get_span_context().trace_id,
            )

        self.assertIsNotNone(entry.propagation_context.traceparent)
        self.assertIn(expected_trace_id, entry.propagation_context.traceparent)

    def test_entry_carries_the_sandbox_id_as_baggage(self) -> None:
        with self.tracer.start_as_current_span("create-wallet"):
            attachment_token = attach_sandbox_id("nikita")
            entry = _build_wallet_created_entry()
            detach_sandbox_id(attachment_token)

        self.assertEqual(entry.propagation_context.baggage, "sandbox-id=nikita")

    def test_baseline_entry_carries_no_sandbox_baggage(self) -> None:
        with self.tracer.start_as_current_span("create-wallet"):
            entry = _build_wallet_created_entry()

        self.assertIsNone(entry.propagation_context.baggage)
