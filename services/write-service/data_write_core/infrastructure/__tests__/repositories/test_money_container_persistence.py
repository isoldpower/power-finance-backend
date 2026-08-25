"""Round-trips through the real ORM for the container base table.

The rest of the write-service suite works against repository fakes, which is fine
for everything the domain decides but says nothing about the two things this
mapping actually relies on: that saving a subclass writes both tables with the
right discriminator, and that a transaction's single container key holds the arc
together as well as the two nullable ones did.
"""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from django.contrib.auth.models import User
from django.db.models import ProtectedError
from django.test import TestCase

from data_write_core.domain.entities import GoalEntity, TransactionEntity, WalletEntity
from data_write_core.domain.exceptions import MoneyContainerNotFoundError
from data_write_core.domain.value_objects import (
    GoalData,
    MoneyContainerKind,
    TransactionMetadata,
    TransactionOrigin,
    WalletData,
)
from data_write_core.infrastructure.orm import GoalModel, MoneyContainerModel, WalletModel
from data_write_core.infrastructure.repositories import (
    DjangoGoalRepository,
    DjangoMoneyContainerRepository,
    DjangoTransactionRepository,
    DjangoWalletRepository,
)

NOW = datetime(2026, 8, 24, 12, 0, tzinfo=UTC)


class MoneyContainerPersistenceTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.user = User.objects.create_user(username="container-owner")

    def _wallet_entity(self, title: str = "Cash", currency: str = "USD") -> WalletEntity:
        return WalletEntity.create(
            data=WalletData(
                title=title,
                currency_code=currency,
                category="daily",
                color="#ffffff",
                favorite=True,
                zero_balance=Decimal("0"),
            ),
            id=str(uuid4()),
            user_id=str(self.user.id),
            created_at=NOW,
            updated_at=NOW,
        )

    def _goal_entity(self, title: str = "Laptop", currency: str = "EUR") -> GoalEntity:
        return GoalEntity.create(
            data=GoalData(
                title=title,
                currency_code=currency,
                target=Decimal("1500.00"),
                finish_at=None,
                url=None,
            ),
            id=str(uuid4()),
            user_id=str(self.user.id),
            created_at=NOW,
        )

    async def _transaction_on(self, container_id: UUID, kind: MoneyContainerKind):
        return await DjangoTransactionRepository().create_transaction(
            TransactionEntity.create(
                id=uuid4(),
                user_id=self.user.id,
                container_id=container_id,
                container_kind=kind,
                metadata=TransactionMetadata(
                    name="Coffee",
                    category=None,
                    evidence_url=None,
                    origin=TransactionOrigin.MANUAL,
                    chain_id=None,
                ),
                created_at=NOW,
            )
        )

    async def test_saving_a_wallet_writes_a_container_row_stamped_as_a_wallet(self) -> None:
        stored = await DjangoWalletRepository().create_wallet(self._wallet_entity())

        container = await MoneyContainerModel.objects.aget(id=stored.unique_id)
        self.assertEqual(container.kind, MoneyContainerModel.WALLET)
        self.assertEqual(container.name, "Cash")
        self.assertEqual(container.currency_id, "USD")
        self.assertEqual(container.user_id, self.user.id)

    async def test_saving_a_goal_writes_a_container_row_stamped_as_a_goal(self) -> None:
        stored = await DjangoGoalRepository().create_goal(self._goal_entity())

        container = await MoneyContainerModel.objects.aget(id=stored.unique_id)
        self.assertEqual(container.kind, MoneyContainerModel.GOAL)
        self.assertEqual(container.name, "Laptop")
        self.assertEqual(container.currency_id, "EUR")

    async def test_the_child_row_shares_the_parent_id(self) -> None:
        wallet = await DjangoWalletRepository().create_wallet(self._wallet_entity())

        stored = await WalletModel.objects.aget(id=wallet.unique_id)
        self.assertEqual(str(stored.container_id), wallet.unique_id)
        self.assertEqual(stored.zero_balance, Decimal("0"))
        self.assertEqual(stored.category, "daily")

    async def test_wallets_and_goals_resolve_through_one_lookup(self) -> None:
        wallet = await DjangoWalletRepository().create_wallet(self._wallet_entity())
        goal = await DjangoGoalRepository().create_goal(self._goal_entity())
        repository = DjangoMoneyContainerRepository()

        wallet_reference = await repository.resolve(UUID(wallet.unique_id), self.user.id)
        goal_reference = await repository.resolve(UUID(goal.unique_id), self.user.id)

        self.assertIs(wallet_reference.kind, MoneyContainerKind.WALLET)
        self.assertEqual(wallet_reference.title, "Cash")
        self.assertEqual(wallet_reference.currency_code, "USD")
        self.assertIs(goal_reference.kind, MoneyContainerKind.GOAL)
        self.assertEqual(goal_reference.currency_code, "EUR")
        self.assertFalse(goal_reference.is_closed)

    async def test_resolve_many_returns_both_kinds_from_a_single_query(self) -> None:
        wallet = await DjangoWalletRepository().create_wallet(self._wallet_entity())
        goal = await DjangoGoalRepository().create_goal(self._goal_entity())
        wanted = [UUID(wallet.unique_id), UUID(goal.unique_id)]

        resolved = await DjangoMoneyContainerRepository().resolve_many(wanted, self.user.id)

        self.assertEqual(set(resolved), set(wanted))
        self.assertIs(resolved[wanted[0]].kind, MoneyContainerKind.WALLET)
        self.assertIs(resolved[wanted[1]].kind, MoneyContainerKind.GOAL)

    async def test_an_unknown_id_is_a_single_miss(self) -> None:
        with self.assertRaises(MoneyContainerNotFoundError):
            await DjangoMoneyContainerRepository().resolve(uuid4(), self.user.id)

    async def test_another_users_container_does_not_resolve(self) -> None:
        wallet = await DjangoWalletRepository().create_wallet(self._wallet_entity())
        intruder = await User.objects.acreate_user(username="intruder")

        with self.assertRaises(MoneyContainerNotFoundError):
            await DjangoMoneyContainerRepository().resolve(UUID(wallet.unique_id), intruder.id)

    async def test_a_soft_deleted_container_resolves_as_closed(self) -> None:
        repository = DjangoWalletRepository()
        wallet = await repository.create_wallet(self._wallet_entity())
        wallet.mark_deleted(NOW)
        await repository.save_wallet(wallet)

        reference = await DjangoMoneyContainerRepository().resolve(
            UUID(wallet.unique_id),
            self.user.id,
        )

        self.assertTrue(reference.is_closed)

    async def test_the_soft_delete_manager_still_applies_to_the_subclass(self) -> None:
        repository = DjangoWalletRepository()
        wallet = await repository.create_wallet(self._wallet_entity())
        wallet.mark_deleted(NOW)
        await repository.save_wallet(wallet)

        self.assertEqual(await WalletModel.objects.acount(), 0)
        self.assertEqual(await WalletModel.objects.with_deleted().acount(), 1)

    async def test_a_transaction_reads_its_kind_back_off_the_container(self) -> None:
        goal = await DjangoGoalRepository().create_goal(self._goal_entity())
        created = await self._transaction_on(UUID(goal.unique_id), MoneyContainerKind.GOAL)

        stored = await DjangoTransactionRepository().get_user_transaction_by_id(
            UUID(created.unique_id),
            self.user.id,
        )

        self.assertEqual(str(stored.container_id), goal.unique_id)
        self.assertIs(stored.container_kind, MoneyContainerKind.GOAL)

    async def test_a_container_holding_transactions_cannot_be_hard_deleted(self) -> None:
        wallet = await DjangoWalletRepository().create_wallet(self._wallet_entity())
        await self._transaction_on(UUID(wallet.unique_id), MoneyContainerKind.WALLET)

        with self.assertRaises(ProtectedError):
            await DjangoWalletRepository().hard_delete_wallet(UUID(wallet.unique_id))

    async def test_hard_deleting_a_container_removes_both_rows(self) -> None:
        wallet = await DjangoWalletRepository().create_wallet(self._wallet_entity())

        await DjangoWalletRepository().hard_delete_wallet(UUID(wallet.unique_id))

        self.assertEqual(await WalletModel.objects.with_deleted().acount(), 0)
        self.assertEqual(await MoneyContainerModel.objects.with_deleted().acount(), 0)

    async def test_goals_and_wallets_share_one_id_space(self) -> None:
        await DjangoWalletRepository().create_wallet(self._wallet_entity())
        await DjangoGoalRepository().create_goal(self._goal_entity())

        self.assertEqual(await MoneyContainerModel.objects.acount(), 2)
        self.assertEqual(await WalletModel.objects.acount(), 1)
        self.assertEqual(await GoalModel.objects.acount(), 1)
