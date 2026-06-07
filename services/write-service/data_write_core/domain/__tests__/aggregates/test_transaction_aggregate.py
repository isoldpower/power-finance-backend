"""TransactionAggregate: delete_self / adjust_self guards and inverse/adjustment construction.

The aggregate owns the rules around what can be cancelled and adjusted:
inverse transactions can't be cancelled, already-cancelled originals can't
be cancelled twice, adjustment transactions can't themselves be adjusted,
and a no-op adjustment to the same amount must short-circuit.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from django.test import SimpleTestCase

from data_write_core.domain.aggregates import TransactionAggregate
from data_write_core.domain.entities import TransactionEntity
from data_write_core.domain.events import EventCollector, TransactionDeletedEvent
from data_write_core.domain.exceptions import (
    CannotAdjustAdjustmentTransactionError,
    CannotCancelInverseTransactionError,
    TransactionAlreadyAdjustedError,
    TransactionAlreadyCancelledError,
)
from data_write_core.domain.value_objects import TransactionData


def _txn(
    *,
    amount: Decimal = Decimal("10"),
    wallet_id: UUID | None = None,
    cancels_other: UUID | None = None,
    adjusts_other: UUID | None = None,
    collector: EventCollector | None = None,
) -> TransactionEntity:
    return TransactionEntity.from_persistence(
        id=uuid4(),
        user_id=3,
        created_at=datetime(2026, 1, 1, 10),
        data=TransactionData(
            source_wallet_id=wallet_id or uuid4(),
            amount=amount,
            cancels_other=cancels_other,
            adjusts_other=adjusts_other,
        ),
        _event_collector=collector,
    )


class DeleteSelfTests(SimpleTestCase):
    def test_creates_inverse_with_negated_amount_and_back_link(self) -> None:
        collector = EventCollector()
        original = _txn(amount=Decimal("25"), collector=collector)
        aggregate = TransactionAggregate(original, cancelled_by=None, adjusted_by=None)

        inverse = aggregate.delete_self()

        self.assertEqual(inverse.amount, Decimal("-25"))
        self.assertEqual(inverse.cancels_other, UUID(original.unique_id))
        self.assertEqual(inverse.source_wallet_id, original.source_wallet_id)

    def test_emits_transaction_deleted_event_with_inverse_reference(self) -> None:
        collector = EventCollector()
        original = _txn(amount=Decimal("25"), collector=collector)
        aggregate = TransactionAggregate(original, cancelled_by=None, adjusted_by=None)

        inverse = aggregate.delete_self()
        events = aggregate.pull_events()

        deleted_events = [e for e in events if isinstance(e, TransactionDeletedEvent)]
        self.assertEqual(len(deleted_events), 1)
        evt = deleted_events[0]
        self.assertEqual(evt.transaction_id, UUID(original.unique_id))
        self.assertEqual(evt.cancelled_by, UUID(inverse.unique_id))
        self.assertEqual(evt.amount, original.amount)

    def test_cancelling_an_inverse_transaction_is_rejected(self) -> None:
        # cancels_other != None means this IS an inverse; can't cancel it.
        inverse = _txn(cancels_other=uuid4())
        aggregate = TransactionAggregate(inverse, cancelled_by=None, adjusted_by=None)

        with self.assertRaises(CannotCancelInverseTransactionError) as ctx:
            aggregate.delete_self()

        self.assertEqual(ctx.exception.transaction_id, UUID(inverse.unique_id))

    def test_cancelling_already_cancelled_transaction_is_rejected(self) -> None:
        original = _txn()
        prior_inverse = _txn(cancels_other=UUID(original.unique_id))
        aggregate = TransactionAggregate(original, cancelled_by=prior_inverse, adjusted_by=None)

        with self.assertRaises(TransactionAlreadyCancelledError) as ctx:
            aggregate.delete_self()

        self.assertEqual(ctx.exception.transaction_id, UUID(original.unique_id))

    def test_delete_self_updates_internal_cancelled_by_to_prevent_double_cancel(self) -> None:
        # First delete succeeds; immediately calling again on the same
        # aggregate must raise because state advanced in-memory.
        original = _txn()
        aggregate = TransactionAggregate(original, cancelled_by=None, adjusted_by=None)

        aggregate.delete_self()

        with self.assertRaises(TransactionAlreadyCancelledError):
            aggregate.delete_self()


class AdjustSelfTests(SimpleTestCase):
    def test_emits_delta_adjustment_transaction(self) -> None:
        # Adjustment is an append, not a mutation: a new transaction
        # carrying the *delta* (new - old) and linked via adjusts_other.
        original = _txn(amount=Decimal("100"))
        aggregate = TransactionAggregate(original, cancelled_by=None, adjusted_by=None)

        adjustment = aggregate.adjust_self(new_amount=Decimal("120"))

        self.assertEqual(adjustment.amount, Decimal("20"))
        self.assertEqual(adjustment.adjusts_other, UUID(original.unique_id))
        self.assertIsNone(adjustment.cancels_other)
        self.assertEqual(adjustment.source_wallet_id, original.source_wallet_id)

    def test_negative_delta_when_amount_decreased(self) -> None:
        original = _txn(amount=Decimal("100"))
        aggregate = TransactionAggregate(original, cancelled_by=None, adjusted_by=None)

        adjustment = aggregate.adjust_self(new_amount=Decimal("80"))

        self.assertEqual(adjustment.amount, Decimal("-20"))

    def test_adjustment_to_same_amount_returns_original_without_event(self) -> None:
        # Short-circuit: nothing changes ⇒ no new transaction, no event.
        collector = EventCollector()
        original = _txn(amount=Decimal("50"), collector=collector)
        aggregate = TransactionAggregate(original, cancelled_by=None, adjusted_by=None)

        returned = aggregate.adjust_self(new_amount=Decimal("50"))

        self.assertIs(returned, original)
        self.assertEqual(aggregate.pull_events(), [])

    def test_adjusting_an_adjustment_transaction_is_rejected(self) -> None:
        adjustment_txn = _txn(adjusts_other=uuid4())
        aggregate = TransactionAggregate(adjustment_txn, cancelled_by=None, adjusted_by=None)

        with self.assertRaises(CannotAdjustAdjustmentTransactionError) as ctx:
            aggregate.adjust_self(new_amount=Decimal("99"))

        self.assertEqual(ctx.exception.transaction_id, UUID(adjustment_txn.unique_id))

    def test_already_adjusted_transaction_is_rejected(self) -> None:
        original = _txn(amount=Decimal("10"))
        prior_adjustment = _txn(adjusts_other=UUID(original.unique_id))
        aggregate = TransactionAggregate(original, cancelled_by=None, adjusted_by=prior_adjustment)

        with self.assertRaises(TransactionAlreadyAdjustedError) as ctx:
            aggregate.adjust_self(new_amount=Decimal("99"))

        self.assertEqual(ctx.exception.transaction_id, UUID(original.unique_id))

    def test_adjust_self_updates_internal_state_to_prevent_double_adjust(self) -> None:
        original = _txn(amount=Decimal("10"))
        aggregate = TransactionAggregate(original, cancelled_by=None, adjusted_by=None)

        aggregate.adjust_self(new_amount=Decimal("15"))

        with self.assertRaises(TransactionAlreadyAdjustedError):
            aggregate.adjust_self(new_amount=Decimal("20"))


class TransactionAggregateBasicsTests(SimpleTestCase):
    def test_unique_id_proxies_to_root(self) -> None:
        original = _txn()
        aggregate = TransactionAggregate(original, cancelled_by=None, adjusted_by=None)

        self.assertEqual(aggregate.unique_id, original.unique_id)

    def test_event_collector_proxies_to_root(self) -> None:
        collector = EventCollector()
        original = _txn(collector=collector)
        aggregate = TransactionAggregate(original, cancelled_by=None, adjusted_by=None)

        self.assertIs(aggregate.event_collector, collector)
