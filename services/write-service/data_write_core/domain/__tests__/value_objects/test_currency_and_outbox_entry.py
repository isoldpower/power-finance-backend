"""Small value objects: Currency (ISO 4217 record) and OutboxEntry."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from django.test import SimpleTestCase

from data_write_core.domain.value_objects.currency import Currency
from data_write_core.domain.value_objects.outbox_entry import OutboxEntry


class CurrencyTests(SimpleTestCase):
    def test_currency_is_value_equal_when_all_fields_match(self) -> None:
        a = Currency(code="USD", name="US Dollar", numeric="840", digits=2)
        b = Currency(code="USD", name="US Dollar", numeric="840", digits=2)

        self.assertEqual(a, b)

    def test_currency_is_unequal_when_any_field_differs(self) -> None:
        self.assertNotEqual(
            Currency(code="USD", name="US Dollar", numeric="840", digits=2),
            Currency(code="USD", name="US Dollar", numeric="840", digits=4),
        )

    def test_currency_is_hashable(self) -> None:
        currency = Currency(code="USD", name="US Dollar", numeric="840", digits=2)

        self.assertIn(currency, {currency})


class OutboxEntryTests(SimpleTestCase):
    def test_outbox_entry_preserves_all_fields(self) -> None:
        event_id = uuid4()
        occurred_at = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
        payload = {"transaction_id": "abc", "amount": "10"}

        entry = OutboxEntry(
            event_id=event_id,
            event_type="TransactionCreated",
            aggregate_type="transaction",
            aggregate_id="abc",
            partition_key="42",
            occurred_at=occurred_at,
            schema_version=1,
            payload=payload,
        )

        self.assertEqual(entry.event_id, event_id)
        self.assertEqual(entry.event_type, "TransactionCreated")
        self.assertEqual(entry.aggregate_type, "transaction")
        self.assertEqual(entry.aggregate_id, "abc")
        self.assertEqual(entry.partition_key, "42")
        self.assertEqual(entry.occurred_at, occurred_at)
        self.assertEqual(entry.schema_version, 1)
        self.assertEqual(entry.payload, payload)

    def test_outbox_entry_is_frozen_dataclass(self) -> None:
        entry = OutboxEntry(
            event_id=uuid4(),
            event_type="WalletCreated",
            aggregate_type="wallet",
            aggregate_id="abc",
            partition_key="42",
            occurred_at=datetime.now(UTC),
            schema_version=1,
            payload={},
        )

        with self.assertRaises(Exception):
            entry.event_type = "Tampered"  # type: ignore[misc]
