from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from django.test import SimpleTestCase

from data_write_core.domain.aggregates import TransactionAggregate
from data_write_core.domain.entities import MoneyFlowEntity, TransactionEntity
from data_write_core.domain.events import (
    EventCollector,
    TransactionDeletedEvent,
    TransactionUpdatedEvent,
)
from data_write_core.domain.exceptions import (
    InvalidTransactionAmountError,
    TransactionAlreadyCancelledError,
    TransactionDirectionChangeError,
)
from data_write_core.domain.value_objects import (
    MoneyFlowData,
    TransactionMetadata,
    TransactionType,
)

TRANSACTION_ID = UUID("11111111-1111-1111-1111-111111111111")
WALLET_ID = UUID("22222222-2222-2222-2222-222222222222")


def _transaction(
    *,
    collector: EventCollector | None = None,
    deleted_at: datetime | None = None,
    name: str = "Groceries",
    category: str | None = None,
) -> TransactionEntity:
    return TransactionEntity(
        id=TRANSACTION_ID,
        user_id="9",
        wallet_id=WALLET_ID,
        metadata=TransactionMetadata(name=name, category=category),
        created_at=datetime(2026, 1, 1),
        deleted_at=deleted_at,
        event_collector=collector or EventCollector(),
    )


def _flow(
    amount: str,
    *,
    cancels_other: UUID | None = None,
    adjusts_other: UUID | None = None,
) -> MoneyFlowEntity:
    return MoneyFlowEntity.from_persistence(
        id=uuid4(),
        user_id=9,
        created_at=datetime(2026, 1, 1),
        data=MoneyFlowData(
            transaction_id=TRANSACTION_ID,
            source_wallet_id=WALLET_ID,
            amount=Decimal(amount),
            cancels_other=cancels_other,
            adjusts_other=adjusts_other,
        ),
    )


def _aggregate(*flows: MoneyFlowEntity, **kwargs) -> TransactionAggregate:
    return TransactionAggregate(
        transaction_entity=_transaction(collector=EventCollector(), **kwargs),
        flows=list(flows),
    )


class TransactionAmountTests(SimpleTestCase):
    def test_a_single_flow_is_the_amount(self) -> None:
        self.assertEqual(_aggregate(_flow("-50")).amount, Decimal("-50"))

    def test_adjustments_fold_in(self) -> None:
        aggregate = _aggregate(_flow("-50"), _flow("-20", adjusts_other=uuid4()))

        self.assertEqual(aggregate.amount, Decimal("-70"))

    def test_a_cancelling_flow_is_excluded_from_the_stated_amount(self) -> None:
        """A cancelled transaction still reports the figure it was for — that is
        what DELETE echoes back and what detail shows beside `deleted_at`."""

        aggregate = _aggregate(_flow("-50"), _flow("50", cancels_other=uuid4()))

        self.assertEqual(aggregate.amount, Decimal("-50"))

    def test_ledger_effect_counts_every_flow(self) -> None:
        """The wallet balance is a different question, and it nets to zero."""

        aggregate = _aggregate(_flow("-50"), _flow("50", cancels_other=uuid4()))

        self.assertEqual(aggregate.ledger_effect, Decimal("0"))


class TransactionTypeTests(SimpleTestCase):
    def test_negative_money_is_an_expense(self) -> None:
        self.assertIs(_aggregate(_flow("-50")).type, TransactionType.EXPENSE)

    def test_positive_money_is_an_income(self) -> None:
        self.assertIs(_aggregate(_flow("50")).type, TransactionType.INCOME)

    def test_type_follows_the_fold_not_the_first_flow(self) -> None:
        aggregate = _aggregate(_flow("-50"), _flow("30", adjusts_other=uuid4()))

        self.assertEqual(aggregate.amount, Decimal("-20"))
        self.assertIs(aggregate.type, TransactionType.EXPENSE)


class TransactionAdjustTests(SimpleTestCase):
    def test_adjusting_appends_the_difference(self) -> None:
        aggregate = _aggregate(_flow("-50"))

        adjusting = aggregate.adjust(Decimal("-70"))

        self.assertIsNotNone(adjusting)
        self.assertEqual(adjusting.amount, Decimal("-20"))
        self.assertEqual(aggregate.amount, Decimal("-70"))
        self.assertEqual(len(aggregate.flows), 2)

    def test_adjusting_links_back_to_the_opening_flow(self) -> None:
        opening = _flow("-50")
        aggregate = TransactionAggregate(
            transaction_entity=_transaction(collector=EventCollector()),
            flows=[opening],
        )

        adjusting = aggregate.adjust(Decimal("-70"))

        self.assertEqual(adjusting.adjusts_other, UUID(opening.unique_id))

    def test_adjusting_emits_the_previous_and_new_figures(self) -> None:
        aggregate = _aggregate(_flow("-50"))

        aggregate.adjust(Decimal("-70"))
        events = [
            event for event in aggregate.pull_events() if isinstance(event, TransactionUpdatedEvent)
        ]

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].previous_amount, Decimal("-50"))
        self.assertEqual(events[0].new_amount, Decimal("-70"))

    def test_adjusting_to_the_same_figure_does_nothing(self) -> None:
        aggregate = _aggregate(_flow("-50"))

        self.assertIsNone(aggregate.adjust(Decimal("-50")))
        self.assertEqual(len(aggregate.flows), 1)
        self.assertEqual(aggregate.pull_events(), [])

    def test_adjusting_across_zero_is_refused(self) -> None:
        """Type is the sign of the money, so this would silently turn an
        expense into an income."""

        aggregate = _aggregate(_flow("-50"))

        with self.assertRaises(TransactionDirectionChangeError):
            aggregate.adjust(Decimal("30"))

    def test_adjusting_to_zero_is_refused(self) -> None:
        aggregate = _aggregate(_flow("-50"))

        with self.assertRaises(InvalidTransactionAmountError):
            aggregate.adjust(Decimal("0"))

    def test_adjusting_a_cancelled_transaction_is_refused(self) -> None:
        aggregate = _aggregate(_flow("-50"), deleted_at=datetime(2026, 2, 1))

        with self.assertRaises(TransactionAlreadyCancelledError):
            aggregate.adjust(Decimal("-70"))


class TransactionCancelTests(SimpleTestCase):
    def test_cancelling_appends_an_inverse_and_stamps_the_transaction(self) -> None:
        aggregate = _aggregate(_flow("-50"))
        moment = datetime(2026, 3, 1)

        inverse = aggregate.cancel(moment)

        self.assertEqual(inverse.amount, Decimal("50"))
        self.assertEqual(aggregate.root.deleted_at, moment)
        self.assertEqual(aggregate.ledger_effect, Decimal("0"))

    def test_cancelling_leaves_the_stated_amount_alone(self) -> None:
        aggregate = _aggregate(_flow("-50"))

        aggregate.cancel(datetime(2026, 3, 1))

        self.assertEqual(aggregate.amount, Decimal("-50"))

    def test_cancelling_reverses_adjustments_too(self) -> None:
        aggregate = _aggregate(_flow("-50"), _flow("-20", adjusts_other=uuid4()))

        inverse = aggregate.cancel(datetime(2026, 3, 1))

        self.assertEqual(inverse.amount, Decimal("70"))
        self.assertEqual(aggregate.ledger_effect, Decimal("0"))

    def test_cancelling_emits_the_outstanding_amount(self) -> None:
        aggregate = _aggregate(_flow("-50"))

        aggregate.cancel(datetime(2026, 3, 1))
        events = [
            event for event in aggregate.pull_events() if isinstance(event, TransactionDeletedEvent)
        ]

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].amount, Decimal("-50"))

    def test_cancelling_twice_is_a_no_op(self) -> None:
        """DELETE answers 200 with the same body on a repeat, so the second
        call must not append a second inverse."""

        aggregate = _aggregate(_flow("-50"))
        aggregate.cancel(datetime(2026, 3, 1))
        aggregate.pull_events()

        self.assertIsNone(aggregate.cancel(datetime(2026, 4, 1)))
        self.assertEqual(len(aggregate.flows), 2)
        self.assertEqual(aggregate.pull_events(), [])


class TransactionMetadataTests(SimpleTestCase):
    def test_patching_leaves_unmentioned_fields_alone(self) -> None:
        aggregate = _aggregate(_flow("-50"), name="Old", category="Food")

        aggregate.update_metadata(now=datetime(2026, 2, 1), name="New")

        self.assertEqual(aggregate.root.name, "New")
        self.assertEqual(aggregate.root.category, "Food")

    def test_clearing_a_field_differs_from_omitting_it(self) -> None:
        aggregate = _aggregate(_flow("-50"), category="Food")

        aggregate.update_metadata(now=datetime(2026, 2, 1), category=None)

        self.assertIsNone(aggregate.root.category)

    def test_patching_never_touches_the_money(self) -> None:
        aggregate = _aggregate(_flow("-50"))

        aggregate.update_metadata(now=datetime(2026, 2, 1), name="Renamed")

        self.assertEqual(aggregate.amount, Decimal("-50"))
        self.assertEqual(len(aggregate.flows), 1)

    def test_a_patch_that_changes_nothing_reports_so(self) -> None:
        aggregate = _aggregate(_flow("-50"), name="Same")

        self.assertFalse(aggregate.update_metadata(now=datetime(2099, 1, 1), name="Same"))
