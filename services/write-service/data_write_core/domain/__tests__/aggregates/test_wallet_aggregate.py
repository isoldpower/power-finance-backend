"""WalletAggregate: balance derivation, apply_transaction, rename, soft_delete
(balance = checkpoint + sum(unsettled), idempotent no-op mutations)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from django.test import SimpleTestCase

from data_write_core.domain.aggregates import WalletAggregate
from data_write_core.domain.entities import (
    BalanceCheckpointEntity,
    TransactionEntity,
    WalletEntity,
)
from data_write_core.domain.events import (
    EventCollector,
    TransactionCreatedEvent,
    WalletDeletedEvent,
    WalletUpdatedEvent,
)
from data_write_core.domain.exceptions import InvalidTransactionAmountError
from data_write_core.domain.value_objects import TransactionData, WalletData


def _wallet(
    *,
    wallet_id: str = "11111111-1111-1111-1111-111111111111",
    title: str = "Main",
    collector: EventCollector | None = None,
    deleted_at: datetime | None = None,
) -> WalletEntity:
    now = datetime(2026, 1, 1)
    return WalletEntity.create(
        id=wallet_id,
        user_id="9",
        data=WalletData(title=title, currency_code="USD"),
        created_at=now,
        updated_at=now,
        deleted_at=deleted_at,
        _event_collector=collector,
    )


def _persisted_transaction(amount: Decimal, wallet_id: UUID) -> TransactionEntity:
    """Transaction reconstituted from storage (no creation event)."""
    return TransactionEntity.from_persistence(
        id=uuid4(),
        user_id=9,
        created_at=datetime(2026, 1, 1, 12),
        data=TransactionData(
            source_wallet_id=wallet_id,
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
        external_list: list[TransactionEntity] = []

        aggregate = WalletAggregate(
            wallet_entity=wallet,
            unsettled_transactions=external_list,
            balance_checkpoint=None,
        )
        aggregate.apply_transaction(Decimal("1"))

        self.assertEqual(external_list, [])


class WalletAggregateApplyTransactionTests(SimpleTestCase):
    def test_apply_transaction_increases_balance(self) -> None:
        wallet = _wallet()
        aggregate = WalletAggregate(wallet, unsettled_transactions=[], balance_checkpoint=None)

        aggregate.apply_transaction(Decimal("25.50"))

        self.assertEqual(aggregate.balance, Decimal("25.50"))

    def test_apply_transaction_returns_transaction_with_correct_wallet_link(self) -> None:
        wallet = _wallet()
        aggregate = WalletAggregate(wallet, [], None)

        txn = aggregate.apply_transaction(Decimal("10"))

        self.assertEqual(txn.source_wallet_id, UUID(wallet.unique_id))
        self.assertEqual(txn.amount, Decimal("10"))
        self.assertIsNone(txn.cancels_other)
        self.assertIsNone(txn.adjusts_other)

    def test_apply_transaction_emits_transaction_created_event_via_aggregate_collector(
        self,
    ) -> None:
        collector = EventCollector()
        wallet = _wallet(collector=collector)
        aggregate = WalletAggregate(wallet, [], None)

        aggregate.apply_transaction(Decimal("10"))
        events = aggregate.pull_events()

        self.assertEqual(len(events), 1)
        self.assertIsInstance(events[0], TransactionCreatedEvent)

    def test_zero_amount_transaction_is_rejected(self) -> None:
        wallet = _wallet()
        aggregate = WalletAggregate(wallet, [], None)

        with self.assertRaises(InvalidTransactionAmountError) as ctx:
            aggregate.apply_transaction(Decimal("0"))

        self.assertEqual(ctx.exception.amount, Decimal("0"))

    def test_negative_amount_is_accepted_as_withdrawal(self) -> None:
        wallet = _wallet()
        aggregate = WalletAggregate(wallet, [], None)

        txn = aggregate.apply_transaction(Decimal("-7"))

        self.assertEqual(txn.amount, Decimal("-7"))


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
