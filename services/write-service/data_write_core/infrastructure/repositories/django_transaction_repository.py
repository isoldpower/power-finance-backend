from datetime import datetime
from uuid import UUID

from write_service.common.pagination import PageRequest, apply_keyset

from data_write_core.application.interfaces import TransactionRepository
from data_write_core.domain.entities import TransactionEntity

from ..orm import TransactionChainModel, TransactionModel
from .mappers import TransactionMapper


class DjangoTransactionRepository(TransactionRepository):
    @staticmethod
    def _live(user_id: int):
        return TransactionModel.objects.filter(
            user_id=user_id,
            deleted_at__isnull=True,
        )

    async def create_transaction(self, transaction: TransactionEntity) -> TransactionEntity:
        model = TransactionMapper.apply_to_model(TransactionModel(), transaction)
        await model.asave(force_insert=True)

        return TransactionMapper.to_domain(model)

    async def save_transaction(self, transaction: TransactionEntity) -> TransactionEntity:
        model = await TransactionModel.objects.aget(id=transaction.unique_id)
        TransactionMapper.apply_to_model(model, transaction)
        await model.asave()

        return TransactionMapper.to_domain(model)

    async def get_user_transaction_by_id(
        self,
        transaction_id: UUID,
        user_id: int,
    ) -> TransactionEntity:
        model = await TransactionModel.objects.aget(id=transaction_id, user_id=user_id)

        return TransactionMapper.to_domain(model)

    async def get_user_transactions(
        self,
        user_id: int,
        page: PageRequest | None = None,
    ) -> list[TransactionEntity]:
        queryset = self._live(user_id)
        rows = apply_keyset(queryset, page) if page else queryset.order_by("-created_at", "-id")

        return [TransactionMapper.to_domain(model) async for model in rows]

    async def count_user_transactions(self, user_id: int) -> int:
        return await self._live(user_id).acount()

    async def hard_delete_transaction(self, transaction_id: UUID) -> None:
        await TransactionModel.objects.filter(id=transaction_id).adelete()

    async def create_chain(self, chain_id: UUID, user_id: int, created_at: datetime) -> None:
        await TransactionChainModel.objects.acreate(
            id=chain_id,
            user_id=user_id,
            created_at=created_at,
        )

    async def get_chain_transactions(
        self,
        chain_id: UUID,
        user_id: int,
    ) -> list[TransactionEntity]:
        rows = TransactionModel.objects.filter(
            chain_id=chain_id,
            user_id=user_id,
        ).order_by("created_at", "id")

        return [TransactionMapper.to_domain(model) async for model in rows]

    async def hard_delete_chain(self, chain_id: UUID) -> None:
        await TransactionModel.objects.filter(chain_id=chain_id).adelete()
        await TransactionChainModel.objects.filter(id=chain_id).adelete()
