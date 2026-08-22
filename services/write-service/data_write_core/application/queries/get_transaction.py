from dataclasses import dataclass
from uuid import UUID

from data_write_core.domain.aggregates import TransactionAggregate

from ..bootstrap import get_repository_registry
from ..dtos import TransactionDTO, transaction_to_dto, wallet_to_dto
from ..interfaces import MoneyFlowRepository, TransactionRepository, WalletRepository


@dataclass(frozen=True)
class GetFallbackTransactionQuery:
    user_id: int
    transaction_id: UUID


class GetFallbackTransactionQueryHandler:
    def __init__(
        self,
        money_flow_repository: MoneyFlowRepository | None = None,
        wallet_repository: WalletRepository | None = None,
        transaction_repository: TransactionRepository | None = None,
    ) -> None:
        if (
            money_flow_repository is None
            or wallet_repository is None
            or (transaction_repository is None)
        ):
            registry = get_repository_registry()
            money_flow_repository = money_flow_repository or registry.money_flow_repository
            wallet_repository = wallet_repository or registry.wallet_repository
            transaction_repository = transaction_repository or registry.transaction_repository

        self._money_flow_repository = money_flow_repository
        self._wallet_repository = wallet_repository
        self._transaction_repository = transaction_repository

    async def handle(self, query: GetFallbackTransactionQuery) -> TransactionDTO:
        transaction = await self._transaction_repository.get_user_transaction_by_id(
            transaction_id=query.transaction_id,
            user_id=query.user_id,
        )
        flows = await self._money_flow_repository.get_flows_for_transaction(query.transaction_id)
        wallet = await self._wallet_repository.get_user_wallet_by_id(
            wallet_id=transaction.wallet_id,
            user_id=query.user_id,
        )

        return transaction_to_dto(
            TransactionAggregate(transaction_entity=transaction, flows=flows),
            wallet_to_dto(wallet),
        )
