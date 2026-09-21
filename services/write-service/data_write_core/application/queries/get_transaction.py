from dataclasses import dataclass
from uuid import UUID

from data_write_core.domain.aggregates import TransactionAggregate

from ..bootstrap import get_repository_registry
from ..dtos import TransactionDTO, container_to_dto, transaction_to_dto
from ..interfaces import (
    MoneyContainerRepository,
    MoneyFlowRepository,
    TransactionRepository,
)


@dataclass(frozen=True)
class GetFallbackTransactionQuery:
    user_id: int
    transaction_id: UUID


class GetFallbackTransactionQueryHandler:
    def __init__(
        self,
        money_flow_repository: MoneyFlowRepository | None = None,
        container_repository: MoneyContainerRepository | None = None,
        transaction_repository: TransactionRepository | None = None,
    ) -> None:
        if (
            money_flow_repository is None
            or container_repository is None
            or (transaction_repository is None)
        ):
            registry = get_repository_registry()
            money_flow_repository = money_flow_repository or registry.money_flow_repository
            container_repository = container_repository or registry.money_container_repository
            transaction_repository = transaction_repository or registry.transaction_repository

        self._money_flow_repository = money_flow_repository
        self._container_repository = container_repository
        self._transaction_repository = transaction_repository

    async def handle(self, query: GetFallbackTransactionQuery) -> TransactionDTO:
        transaction = await self._transaction_repository.get_user_transaction_by_id(
            transaction_id=query.transaction_id,
            user_id=query.user_id,
        )
        flows = await self._money_flow_repository.get_flows_for_transaction(query.transaction_id)
        container = await self._container_repository.resolve(
            container_id=transaction.container_id,
            user_id=query.user_id,
        )

        return transaction_to_dto(
            TransactionAggregate(transaction_entity=transaction, flows=flows),
            container_to_dto(container),
        )
