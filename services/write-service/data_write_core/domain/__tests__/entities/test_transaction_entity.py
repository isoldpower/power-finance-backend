"""TransactionEntity: factory emits TransactionCreatedEvent; create_inverse builds a negating, cancels_other-linked twin."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from django.test import SimpleTestCase

from data_write_core.domain.entities import TransactionEntity
from data_write_core.domain.events import EventCollector, TransactionCreatedEvent
from data_write_core.domain.value_objects import TransactionData


def _txn_data(amount: Decimal = Decimal("10"), wallet_id: UUID | None = None) -> TransactionData:
    return TransactionData(
        source_wallet_id=wallet_id or uuid4(),
        amount=amount,
        cancels_other=None,
        adjusts_other=None,
    )


class TransactionEntityCreateTests(SimpleTestCase):
    def test_create_emits_a_single_transaction_created_event(self) -> None:
        collector = EventCollector()

        txn = TransactionEntity.create(
            user_id=42,
            data=_txn_data(),
            _event_collector=collector,
        )
        events = collector.pull_events()

        self.assertEqual(len(events), 1)
        event = events[0]
        self.assertIsInstance(event, TransactionCreatedEvent)
        self.assertEqual(event.transaction_id, UUID(txn.unique_id))
        self.assertEqual(event.wallet_id, txn.source_wallet_id)
        self.assertEqual(event.user_id, 42)
        self.assertEqual(event.amount, txn.amount)
        self.assertEqual(event.created_at, txn.created_at)

    def test_create_assigns_unique_id_per_call(self) -> None:
        wallet_id = uuid4()
        a = TransactionEntity.create(user_id=1, data=_txn_data(wallet_id=wallet_id))
        b = TransactionEntity.create(user_id=1, data=_txn_data(wallet_id=wallet_id))

        self.assertNotEqual(a.unique_id, b.unique_id)

    def test_create_falls_back_to_default_collector_when_none_provided(self) -> None:
        # Default collector swallows the event; this guards the
        # `or EventCollector()` branch from accidental removal.
        txn = TransactionEntity.create(user_id=1, data=_txn_data())

        self.assertIsInstance(txn.event_collector, EventCollector)

    def test_create_stores_user_id_as_string_but_event_uses_int(self) -> None:
        txn = TransactionEntity.create(user_id=99, data=_txn_data())

        self.assertEqual(txn.user_id, "99")
        # Pull and inspect the previously emitted event:
        events = txn.event_collector.pull_events()
        self.assertEqual(events[0].user_id, 99)


class TransactionEntityFromPersistenceTests(SimpleTestCase):
    def test_from_persistence_does_not_emit_creation_event(self) -> None:
        # Reconstituting a stored transaction must be event-silent.
        collector = EventCollector()

        TransactionEntity.from_persistence(
            id=uuid4(),
            user_id=1,
            created_at=datetime(2026, 1, 1, 12, 0, 0),
            data=_txn_data(),
            _event_collector=collector,
        )

        self.assertEqual(collector.pull_events(), [])

    def test_from_persistence_round_trips_all_data(self) -> None:
        txn_id = uuid4()
        wallet_id = uuid4()
        created_at = datetime(2026, 5, 20, 10, 30, 0)

        txn = TransactionEntity.from_persistence(
            id=txn_id,
            user_id=7,
            created_at=created_at,
            data=TransactionData(
                source_wallet_id=wallet_id,
                amount=Decimal("12.50"),
                cancels_other=None,
                adjusts_other=None,
            ),
        )

        self.assertEqual(txn.unique_id, str(txn_id))
        self.assertEqual(txn.user_id, "7")
        self.assertEqual(txn.created_at, created_at)
        self.assertEqual(txn.source_wallet_id, wallet_id)
        self.assertEqual(txn.amount, Decimal("12.50"))


class TransactionEntityInverseTests(SimpleTestCase):
    def test_create_inverse_negates_amount(self) -> None:
        original = TransactionEntity.create(user_id=1, data=_txn_data(amount=Decimal("15")))
        original.event_collector.pull_events()  # discard creation event

        inverse = original.create_inverse(event_collector=EventCollector())

        self.assertEqual(inverse.amount, Decimal("-15"))

    def test_create_inverse_links_back_via_cancels_other(self) -> None:
        original = TransactionEntity.create(user_id=1, data=_txn_data())

        inverse = original.create_inverse(event_collector=EventCollector())

        self.assertEqual(inverse.cancels_other, UUID(original.unique_id))
        self.assertIsNone(inverse.adjusts_other)

    def test_create_inverse_preserves_source_wallet_and_user(self) -> None:
        wallet_id = uuid4()
        original = TransactionEntity.create(
            user_id=88, data=_txn_data(amount=Decimal("3"), wallet_id=wallet_id)
        )

        inverse = original.create_inverse(event_collector=EventCollector())

        self.assertEqual(inverse.source_wallet_id, wallet_id)
        self.assertEqual(inverse.user_id, "88")

    def test_create_inverse_emits_creation_event_for_inverse(self) -> None:
        # Inverse is a brand-new transaction; it deserves its own
        # TransactionCreatedEvent on its own collector.
        original = TransactionEntity.create(user_id=1, data=_txn_data())
        inverse_collector = EventCollector()

        inverse = original.create_inverse(event_collector=inverse_collector)
        events = inverse_collector.pull_events()

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].transaction_id, UUID(inverse.unique_id))
