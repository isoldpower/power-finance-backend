"""build_outbox_entry: envelope stamping for proto messages → OutboxEntry."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from django.test import SimpleTestCase
from kafka_messages import TransactionCreated, WalletCreated

from data_write_core.domain.value_objects import OutboxEntry
from data_write_core.infrastructure.messaging.proto import (
    build_outbox_entry,
    datetime_to_timestamp,
)


class DatetimeToTimestampTests(SimpleTestCase):
    def test_roundtrips_datetime_via_protobuf_timestamp(self) -> None:
        original = datetime(2026, 5, 26, 10, 0, 0, tzinfo=UTC)

        ts = datetime_to_timestamp(original)

        self.assertEqual(ts.ToDatetime().replace(tzinfo=UTC), original)


class BuildOutboxEntryTests(SimpleTestCase):
    def test_stamps_event_id_on_message_and_outbox_entry_consistently(self) -> None:
        # event_id is stamped onto the proto AND echoed into the entry —
        # consumers correlate by matching these.
        message = TransactionCreated(
            transaction_id="t-1",
            wallet_id="w-1",
            user_id=1,
            amount="10",
        )

        entry = build_outbox_entry(
            message,
            aggregate_type="transaction",
            aggregate_id="t-1",
            partition_key="user_2abc",
        )

        self.assertEqual(entry.event_id, UUID(message.event_id))

    def test_returns_outbox_entry_with_proto_descriptor_name(self) -> None:
        message = WalletCreated(
            wallet_id="w-1",
            user_id=2,
            title="Main",
            currency_code="USD",
        )

        entry = build_outbox_entry(
            message, aggregate_type="wallet", aggregate_id="w-1", partition_key="user_2abc"
        )

        self.assertIsInstance(entry, OutboxEntry)
        self.assertEqual(entry.event_type, "WalletCreated")
        self.assertEqual(entry.aggregate_type, "wallet")
        self.assertEqual(entry.aggregate_id, "w-1")

    def test_default_schema_version_is_set_when_unset(self) -> None:
        message = TransactionCreated(transaction_id="t-1", wallet_id="w-1", user_id=1, amount="1")

        entry = build_outbox_entry(
            message, aggregate_type="transaction", aggregate_id="t-1", partition_key="user_2abc"
        )

        self.assertEqual(entry.schema_version, 1)
        self.assertEqual(message.schema_version, 1)

    def test_explicit_schema_version_is_preserved(self) -> None:
        message = TransactionCreated(transaction_id="t-1", wallet_id="w-1", user_id=1, amount="1")
        message.schema_version = 42

        entry = build_outbox_entry(
            message, aggregate_type="transaction", aggregate_id="t-1", partition_key="user_2abc"
        )

        self.assertEqual(entry.schema_version, 42)

    def test_occurred_at_is_utc_and_set_at_call_time(self) -> None:
        before = datetime.now(UTC)
        message = TransactionCreated(transaction_id="t-1", wallet_id="w-1", user_id=1, amount="1")

        entry = build_outbox_entry(
            message, aggregate_type="transaction", aggregate_id="t-1", partition_key="user_2abc"
        )
        after = datetime.now(UTC)

        self.assertEqual(entry.occurred_at.tzinfo, UTC)
        self.assertLessEqual(before, entry.occurred_at)
        self.assertLessEqual(entry.occurred_at, after)

    def test_payload_preserves_proto_field_names_and_includes_default_fields(self) -> None:
        # preserving_proto_field_name=True ⇒ snake_case in payload.
        # always_print_fields_with_no_presence=True ⇒ defaults included
        # (consumers should never get KeyError on a known field).
        message = TransactionCreated(
            transaction_id="t-9",
            wallet_id="w-9",
            user_id=99,
            amount="1.50",
        )

        entry = build_outbox_entry(
            message, aggregate_type="transaction", aggregate_id="t-9", partition_key="user_2abc"
        )

        self.assertEqual(entry.payload["transaction_id"], "t-9")
        self.assertEqual(entry.payload["wallet_id"], "w-9")
        self.assertIn("user_id", entry.payload)
        self.assertIn("amount", entry.payload)

    def test_partition_key_is_the_user_external_id_verbatim(self) -> None:
        # The partition key becomes the Kafka message key; push-service
        # matches it against the gateway's X-User-Id (Clerk sub) — pin
        # that it passes through untouched.
        message = WalletCreated(wallet_id="w-1", user_id=2, title="Main", currency_code="USD")

        entry = build_outbox_entry(
            message, aggregate_type="wallet", aggregate_id="w-1", partition_key="user_2abc"
        )

        self.assertEqual(entry.partition_key, "user_2abc")

    def test_empty_partition_key_falls_back_to_global(self) -> None:
        message = WalletCreated(wallet_id="w-1", user_id=2, title="Main", currency_code="USD")

        entry = build_outbox_entry(
            message, aggregate_type="wallet", aggregate_id="w-1", partition_key=""
        )

        self.assertEqual(entry.partition_key, "GLOBAL")

    def test_two_calls_produce_distinct_event_ids(self) -> None:
        m1 = TransactionCreated(transaction_id="a", wallet_id="w", user_id=1, amount="1")
        m2 = TransactionCreated(transaction_id="b", wallet_id="w", user_id=1, amount="1")

        e1 = build_outbox_entry(
            m1, aggregate_type="transaction", aggregate_id="a", partition_key="user_2abc"
        )
        e2 = build_outbox_entry(
            m2, aggregate_type="transaction", aggregate_id="b", partition_key="user_2abc"
        )

        self.assertNotEqual(e1.event_id, e2.event_id)
