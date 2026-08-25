from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from django.test import SimpleTestCase

from data_write_core.domain.aggregates import WalletAggregate
from data_write_core.domain.entities import (
    BalanceCheckpointEntity,
    MoneyFlowEntity,
    WalletEntity,
)
from data_write_core.domain.events import (
    EventCollector,
    WalletDeletedEvent,
    WalletUpdatedEvent,
)
from data_write_core.domain.exceptions import WalletNotEmptyError
from data_write_core.domain.value_objects import MoneyFlowData, WalletData


def _wallet(
    *,
    wallet_id: str = "11111111-1111-1111-1111-111111111111",
    title: str = "Main",
    collector: EventCollector | None = None,
    deleted_at: datetime | None = None,
    zero_balance: Decimal = Decimal("0"),
    category: str = "",
    color: str = "",
    favorite: bool = False,
) -> WalletEntity:
    now = datetime(2026, 1, 1)
    return WalletEntity.create(
        id=wallet_id,
        user_id="9",
        data=WalletData(
            title=title,
            currency_code="USD",
            zero_balance=zero_balance,
            category=category,
            color=color,
            favorite=favorite,
        ),
        created_at=now,
        updated_at=now,
        deleted_at=deleted_at,
        _event_collector=collector,
    )


def _persisted_transaction(amount: Decimal, wallet_id: UUID) -> MoneyFlowEntity:
    """Transaction reconstituted from storage (no creation event)."""
    return MoneyFlowEntity.from_persistence(
        id=uuid4(),
        user_id=9,
        created_at=datetime(2026, 1, 1, 12),
        data=MoneyFlowData(
            transaction_id=uuid4(),
            container_id=wallet_id,
            amount=amount,
            cancels_other=None,
            adjusts_other=None,
        ),
    )


class WalletAggregateBalanceTests(SimpleTestCase):
    def test_balance_is_zero_when_no_checkpoint_and_no_transactions(self) -> None:
        wallet = _wallet()

        aggregate = WalletAggregate(
            wallet_entity=wallet,
            unsettled_transactions=[],
            balance_checkpoint=None,
        )

        self.assertEqual(aggregate.balance, Decimal("0"))

    def test_balance_equals_checkpoint_when_no_unsettled(self) -> None:
        wallet = _wallet()

        aggregate = WalletAggregate(
            wallet_entity=wallet,
            unsettled_transactions=[],
            balance_checkpoint=BalanceCheckpointEntity(
                id="ckpt",
                created_at=datetime(2026, 1, 1),
                balance=Decimal("500"),
            ),
        )

        self.assertEqual(aggregate.balance, Decimal("500"))

    def test_balance_sums_checkpoint_and_unsettled_transactions(self) -> None:
        wallet = _wallet()
        wallet_id = UUID(wallet.unique_id)

        aggregate = WalletAggregate(
            wallet_entity=wallet,
            unsettled_transactions=[
                _persisted_transaction(Decimal("100"), wallet_id),
                _persisted_transaction(Decimal("-30"), wallet_id),
                _persisted_transaction(Decimal("5"), wallet_id),
            ],
            balance_checkpoint=BalanceCheckpointEntity(
                id="ckpt",
                created_at=datetime(2026, 1, 1),
                balance=Decimal("200"),
            ),
        )

        self.assertEqual(aggregate.balance, Decimal("275"))

    def test_balance_handles_negative_drift_below_zero(self) -> None:
        wallet = _wallet()
        wallet_id = UUID(wallet.unique_id)

        aggregate = WalletAggregate(
            wallet_entity=wallet,
            unsettled_transactions=[_persisted_transaction(Decimal("-50"), wallet_id)],
            balance_checkpoint=BalanceCheckpointEntity(
                id="ckpt",
                created_at=datetime(2026, 1, 1),
                balance=Decimal("10"),
            ),
        )

        self.assertEqual(aggregate.balance, Decimal("-40"))

    def test_unsettled_transactions_list_is_copied_not_aliased(self) -> None:
        wallet = _wallet()
        external_list: list[MoneyFlowEntity] = []

        aggregate = WalletAggregate(
            wallet_entity=wallet,
            unsettled_transactions=external_list,
            balance_checkpoint=None,
        )
        aggregate.record(_persisted_transaction(Decimal("1"), UUID(wallet.unique_id)))

        self.assertEqual(external_list, [])


class WalletAggregateRecordTests(SimpleTestCase):
    """The wallet folds flows, it does not create them — a flow belongs to a
    transaction, and only the transaction factory mints one."""

    def test_recording_a_flow_moves_the_balance(self) -> None:
        wallet = _wallet()
        aggregate = WalletAggregate(wallet, unsettled_transactions=[], balance_checkpoint=None)

        aggregate.record(_persisted_transaction(Decimal("25.50"), UUID(wallet.unique_id)))

        self.assertEqual(aggregate.balance, Decimal("25.50"))

    def test_recording_a_negative_flow_reduces_the_balance(self) -> None:
        wallet = _wallet()
        aggregate = WalletAggregate(wallet, [], None)

        aggregate.record(_persisted_transaction(Decimal("-7"), UUID(wallet.unique_id)))

        self.assertEqual(aggregate.balance, Decimal("-7"))

    def test_recording_emits_nothing(self) -> None:
        """Folding a pending flow is a read-model concern; the event that
        matters was already collected by the transaction."""

        collector = EventCollector()
        wallet = _wallet(collector=collector)
        aggregate = WalletAggregate(wallet, [], None)

        aggregate.record(_persisted_transaction(Decimal("10"), UUID(wallet.unique_id)))

        self.assertEqual(aggregate.pull_events(), [])


class WalletAggregateRenameTests(SimpleTestCase):
    def test_rename_updates_entity_and_emits_wallet_updated_event(self) -> None:
        collector = EventCollector()
        wallet = _wallet(title="Old", collector=collector)
        aggregate = WalletAggregate(wallet, [], None)
        now = datetime(2026, 2, 1)

        aggregate.rename("New", now)
        events = aggregate.pull_events()

        self.assertEqual(wallet.title, "New")
        self.assertEqual(len(events), 1)
        self.assertIsInstance(events[0], WalletUpdatedEvent)
        self.assertEqual(events[0].previous_title, "Old")
        self.assertEqual(events[0].new_title, "New")
        self.assertEqual(events[0].updated_at, now)

    def test_rename_to_same_title_is_noop_and_emits_nothing(self) -> None:
        collector = EventCollector()
        wallet = _wallet(title="Same", collector=collector)
        original_updated_at = wallet.updated_at
        aggregate = WalletAggregate(wallet, [], None)

        aggregate.rename("Same", datetime(2099, 1, 1))

        self.assertEqual(wallet.title, "Same")
        self.assertEqual(wallet.updated_at, original_updated_at)
        self.assertEqual(aggregate.pull_events(), [])


class WalletAggregateSoftDeleteTests(SimpleTestCase):
    def test_soft_delete_marks_wallet_and_emits_event(self) -> None:
        collector = EventCollector()
        wallet = _wallet(collector=collector)
        aggregate = WalletAggregate(wallet, [], None)
        delete_time = datetime(2026, 3, 1)

        aggregate.soft_delete(delete_time)
        events = aggregate.pull_events()

        self.assertEqual(wallet.deleted_at, delete_time)
        self.assertEqual(len(events), 1)
        self.assertIsInstance(events[0], WalletDeletedEvent)
        self.assertEqual(events[0].deleted_at, delete_time)
        self.assertEqual(events[0].user_id, 9)

    def test_soft_delete_on_already_deleted_wallet_is_idempotent_noop(self) -> None:
        collector = EventCollector()
        wallet = _wallet(collector=collector, deleted_at=datetime(2026, 1, 5))
        aggregate = WalletAggregate(wallet, [], None)

        aggregate.soft_delete(datetime(2026, 2, 1))

        self.assertEqual(wallet.deleted_at, datetime(2026, 1, 5))
        self.assertEqual(aggregate.pull_events(), [])

    def test_event_collector_property_proxies_through_root(self) -> None:
        collector = EventCollector()
        wallet = _wallet(collector=collector)
        aggregate = WalletAggregate(wallet, [], None)

        self.assertIs(aggregate.event_collector, collector)

    def test_unique_id_proxies_to_root(self) -> None:
        wallet = _wallet(wallet_id="22222222-2222-2222-2222-222222222222")
        aggregate = WalletAggregate(wallet, [], None)

        self.assertEqual(aggregate.unique_id, "22222222-2222-2222-2222-222222222222")


class WalletAggregateOwnedTests(SimpleTestCase):
    """`zero_balance` is the datum the balance is measured from, so a credit
    line is spendable but not owned."""

    def _aggregate(self, balance: str, zero_balance: str) -> WalletAggregate:
        wallet = _wallet(zero_balance=Decimal(zero_balance))
        return WalletAggregate(
            wallet_entity=wallet,
            unsettled_transactions=[],
            balance_checkpoint=BalanceCheckpointEntity(
                id="ckpt",
                created_at=datetime(2026, 1, 1),
                balance=Decimal(balance),
            ),
        )

    def test_plain_wallet_owns_its_whole_balance(self) -> None:
        self.assertEqual(self._aggregate("500", "0").owned, Decimal("500"))

    def test_unspent_credit_line_is_owned_by_nobody(self) -> None:
        self.assertEqual(self._aggregate("100", "100").owned, Decimal("0"))

    def test_spending_into_a_credit_line_reports_debt(self) -> None:
        self.assertEqual(self._aggregate("70", "100").owned, Decimal("-30"))

    def test_empty_means_sitting_exactly_on_the_datum(self) -> None:
        self.assertTrue(self._aggregate("100", "100").is_empty)
        self.assertFalse(self._aggregate("150", "100").is_empty)
        self.assertFalse(self._aggregate("80", "100").is_empty)


class WalletAggregateCloseGuardTests(SimpleTestCase):
    """Closing is settled in both directions: money still in the wallet blocks
    it, and so does debt still owed on it."""

    def _aggregate(self, balance: str, zero_balance: str) -> WalletAggregate:
        wallet = _wallet(collector=EventCollector(), zero_balance=Decimal(zero_balance))
        return WalletAggregate(
            wallet_entity=wallet,
            unsettled_transactions=[],
            balance_checkpoint=BalanceCheckpointEntity(
                id="ckpt",
                created_at=datetime(2026, 1, 1),
                balance=Decimal(balance),
            ),
        )

    def test_wallet_on_its_datum_closes(self) -> None:
        aggregate = self._aggregate("100", "100")

        aggregate.soft_delete(datetime(2026, 3, 1))

        self.assertEqual(aggregate.root.deleted_at, datetime(2026, 3, 1))

    def test_wallet_still_holding_money_is_refused(self) -> None:
        aggregate = self._aggregate("150", "100")

        with self.assertRaises(WalletNotEmptyError) as raised:
            aggregate.soft_delete(datetime(2026, 3, 1))

        self.assertEqual(raised.exception.balance, Decimal("150"))
        self.assertEqual(raised.exception.zero_balance, Decimal("100"))
        self.assertIsNone(aggregate.root.deleted_at)

    def test_wallet_still_in_debt_is_refused(self) -> None:
        aggregate = self._aggregate("80", "100")

        with self.assertRaises(WalletNotEmptyError):
            aggregate.soft_delete(datetime(2026, 3, 1))

    def test_already_closed_wallet_never_reaches_the_guard(self) -> None:
        """Repeating DELETE answers 200 with the same body, so a wallet that
        drifted off its datum after closing must not start failing."""

        wallet = _wallet(
            collector=EventCollector(),
            deleted_at=datetime(2026, 1, 5),
            zero_balance=Decimal("100"),
        )
        aggregate = WalletAggregate(
            wallet_entity=wallet,
            unsettled_transactions=[],
            balance_checkpoint=BalanceCheckpointEntity(
                id="ckpt",
                created_at=datetime(2026, 1, 1),
                balance=Decimal("999"),
            ),
        )

        aggregate.soft_delete(datetime(2026, 2, 1))

        self.assertEqual(wallet.deleted_at, datetime(2026, 1, 5))
        self.assertEqual(aggregate.pull_events(), [])


class WalletAggregateMetadataTests(SimpleTestCase):
    def test_partial_update_leaves_unmentioned_fields_alone(self) -> None:
        wallet = _wallet(collector=EventCollector(), category="Savings", color="#FF0000")
        aggregate = WalletAggregate(wallet, [], None)

        aggregate.update_metadata(now=datetime(2026, 2, 1), favorite=True)

        self.assertTrue(wallet.favorite)
        self.assertEqual(wallet.category, "Savings")
        self.assertEqual(wallet.color, "#FF0000")

    def test_clearing_a_field_is_distinguishable_from_omitting_it(self) -> None:
        wallet = _wallet(collector=EventCollector(), category="Savings")
        aggregate = WalletAggregate(wallet, [], None)

        aggregate.update_metadata(now=datetime(2026, 2, 1), category="")

        self.assertEqual(wallet.category, "")

    def test_update_event_carries_the_full_post_update_state(self) -> None:
        wallet = _wallet(collector=EventCollector(), title="Old", category="Savings")
        aggregate = WalletAggregate(wallet, [], None)

        aggregate.update_metadata(
            now=datetime(2026, 2, 1),
            favorite=True,
            zero_balance=Decimal("100"),
        )
        event = aggregate.pull_events()[0]

        self.assertEqual(event.previous_title, "Old")
        self.assertEqual(event.new_title, "Old")
        self.assertEqual(event.category, "Savings")
        self.assertTrue(event.favorite)
        self.assertEqual(event.zero_balance, Decimal("100"))

    def test_update_that_changes_nothing_emits_nothing(self) -> None:
        wallet = _wallet(collector=EventCollector(), category="Savings", favorite=True)
        original_updated_at = wallet.updated_at
        aggregate = WalletAggregate(wallet, [], None)

        aggregate.update_metadata(
            now=datetime(2099, 1, 1),
            category="Savings",
            favorite=True,
        )

        self.assertEqual(wallet.updated_at, original_updated_at)
        self.assertEqual(aggregate.pull_events(), [])
