import asyncio
from uuid import UUID

from data_write_core.domain.aggregates import TransactionAggregate, WalletAggregate

from ..dtos import WalletDTO, wallet_to_dto
from ..interfaces import MoneyFlowRepository, TransactionRepository, WalletRepository


class LoadWalletMixin:
    def __init__(
        self,
        wallet_repository: WalletRepository,
        money_flow_repository: MoneyFlowRepository,
    ) -> None:
        self._money_flow_repository = money_flow_repository
        self._wallet_repository = wallet_repository

    async def load_wallet_aggregate(self, wallet_id: UUID, user_id: int) -> WalletAggregate:
        wallet_entity, checkpoint = await asyncio.gather(
            self._wallet_repository.get_user_wallet_by_id(
                wallet_id=wallet_id,
                user_id=user_id,
            ),
            self._money_flow_repository.get_checkpoint(wallet_id),
        )
        settled_at = checkpoint.created_at.isoformat() if checkpoint else None
        unsettled_transactions = await self._money_flow_repository.get_unsettled_flows(
            wallet_id,
            settled_at,
        )

        return WalletAggregate(
            wallet_entity=wallet_entity,
            unsettled_transactions=unsettled_transactions,
            balance_checkpoint=checkpoint,
        )

    async def load_wallet_dto(self, wallet_id: UUID, user_id: int) -> WalletDTO:
        wallet_aggregate = await self.load_wallet_aggregate(wallet_id, user_id)

        return wallet_to_dto(
            wallet_aggregate.root,
            balance_amount=wallet_aggregate.balance,
        )


class LoadTransactionMixin:
    def __init__(
        self,
        transaction_repository: TransactionRepository,
        money_flow_repository: MoneyFlowRepository,
    ):
        self._transaction_repository = transaction_repository
        self._money_flow_repository = money_flow_repository

    async def load_transaction_aggregate(
        self,
        transaction_id: UUID,
        user_id: int,
    ) -> TransactionAggregate:
        """Cancelled transactions load too — DELETE has to be able to answer 200
        on a repeat, and detail still resolves them."""

        transaction, flows = await asyncio.gather(
            self._transaction_repository.get_user_transaction_by_id(
                transaction_id=transaction_id,
                user_id=user_id,
            ),
            self._money_flow_repository.get_flows_for_transaction(transaction_id),
        )

        return TransactionAggregate(transaction_entity=transaction, flows=flows)
