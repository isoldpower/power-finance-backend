from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from django.contrib.auth.models import User
from django.test import TestCase

from data_write_core.domain.entities import TransactionEntity, WalletEntity
from data_write_core.domain.value_objects import (
    MoneyContainerKind,
    TransactionMetadata,
    TransactionOrigin,
    WalletData,
)
from data_write_core.infrastructure.orm import MoneyContainerModel
from data_write_core.infrastructure.repositories import (
    DjangoDemoSeedRepository,
    DjangoTransactionRepository,
    DjangoWalletRepository,
)

NOW = datetime(2026, 11, 15, 12, 0, tzinfo=UTC)


class DemoSeedPersistenceTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.user = User.objects.create_user(username="demo_seedowner")
        cls.other_user = User.objects.create_user(username="demo_someoneelse")

    async def _create_wallet(self, owner: User) -> WalletEntity:
        return await DjangoWalletRepository().create_wallet(
            WalletEntity.create(
                data=WalletData(
                    title="Everyday account",
                    currency_code="USD",
                    category=None,
                    color="",
                    favorite=False,
                    zero_balance=Decimal("0"),
                ),
                id=str(uuid4()),
                user_id=str(owner.id),
                created_at=NOW,
                updated_at=NOW,
            )
        )

    async def test_a_seed_is_incomplete_until_marked_and_marking_twice_is_harmless(self):
        repository = DjangoDemoSeedRepository()

        self.assertFalse(await repository.is_seed_completed(self.user.id))
        await repository.mark_seed_completed(self.user.id)
        await repository.mark_seed_completed(self.user.id)

        self.assertTrue(await repository.is_seed_completed(self.user.id))
        self.assertFalse(await repository.is_seed_completed(self.other_user.id))

    async def test_existing_seed_items_cover_deleted_containers_and_transactions_of_the_owner(self):
        repository = DjangoDemoSeedRepository()
        wallet = await self._create_wallet(self.user)
        foreign_wallet = await self._create_wallet(self.other_user)
        transaction = await DjangoTransactionRepository().create_transaction(
            TransactionEntity.create(
                id=uuid4(),
                user_id=self.user.id,
                container_id=wallet.unique_id,
                container_kind=MoneyContainerKind.WALLET,
                metadata=TransactionMetadata(name="Salary", origin=TransactionOrigin.MANUAL),
                created_at=NOW,
            )
        )
        missing_item_id = uuid4()
        await MoneyContainerModel.objects.filter(id=wallet.unique_id).aupdate(deleted_at=NOW)

        existing_item_ids = await repository.find_existing_seed_items(
            self.user.id,
            [
                UUID(wallet.unique_id),
                UUID(str(transaction.unique_id)),
                UUID(foreign_wallet.unique_id),
                missing_item_id,
            ],
        )

        self.assertEqual(
            existing_item_ids, {UUID(wallet.unique_id), UUID(str(transaction.unique_id))}
        )
