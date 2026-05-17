import asyncio
from uuid import UUID

from data_write_core.domain.aggregates import TransactionAggregate, WalletAggregate

from ..dtos import WalletDTO, wallet_to_dto
from ..interfaces import TransactionRepository, WalletRepository


class LoadWalletMixin:
    def __init__(
        self,
        wallet_repository: WalletRepository,
        transaction_repository: TransactionRepository,
    ) -> None:
        self._transaction_repository = transaction_repository
        self._wallet_repository = wallet_repository

    async def load_wallet_aggregate(self, wallet_id: UUID, user_id: int) -> WalletAggregate:
        wallet_entity, checkpoint = await asyncio.gather(
            self._wallet_repository.get_user_wallet_by_id(
                wallet_id=wallet_id,
                user_id=user_id,
            ),
            self._transaction_repository.get_checkpoint(wallet_id),
        )
        settled_at = checkpoint.created_at.isoformat() if checkpoint else None
        unsettled_transactions = await self._transaction_repository.get_unsettled_transactions(
            wallet_id,
            settled_at,
        )

        return WalletAggregate(
            wallet_entity=wallet_entity,
            unsettled_transactions=unsettled_transactions,
            balance_checkpoint=checkpoint,
        )

    async def load_wallet_dto(self, wallet_id: UUID, user_id: int) -> WalletDTO:
        wallet_entity, checkpoint = await asyncio.gather(
            self._wallet_repository.get_user_wallet_by_id(
                wallet_id=wallet_id,
                user_id=user_id,
            ),
            self._transaction_repository.get_checkpoint(wallet_id),
        )
        settled_at = checkpoint.created_at.isoformat() if checkpoint else None
        unsettled_transactions = await self._transaction_repository.get_unsettled_transactions(
            wallet_id,
            settled_at,
        )
        wallet_aggregate = WalletAggregate(
            wallet_entity=wallet_entity,
            unsettled_transactions=unsettled_transactions,
            balance_checkpoint=checkpoint,
        )

        return wallet_to_dto(
            wallet_entity,
            balance_amount=wallet_aggregate.balance,
        )


class LoadTransactionMixin:
    def __init__(
        self,
        transaction_repository: TransactionRepository,
    ):
        self._transaction_repository = transaction_repository

    async def load_transaction_aggregate(
        self, transaction_id: UUID, user_id: int
    ) -> TransactionAggregate:
        current_transaction = await self._transaction_repository.get_user_transaction_by_id(
            user_id=user_id,
            transaction_id=transaction_id,
        )
        cancelled_by, adjusted_by = await asyncio.gather(
            self._transaction_repository.get_cancelling_transaction(transaction_id),
            self._transaction_repository.get_adjusting_transaction(transaction_id),
        )
        transaction_aggregate = TransactionAggregate(
            transaction_entity=current_transaction,
            cancelled_by=cancelled_by,
            adjusted_by=adjusted_by,
        )

        return transaction_aggregate
