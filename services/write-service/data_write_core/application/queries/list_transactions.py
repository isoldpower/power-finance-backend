import asyncio
from dataclasses import dataclass
from uuid import UUID

from write_service.common.pagination import PageRequest

from data_write_core.domain.aggregates import TransactionAggregate

from ..bootstrap import get_repository_registry
from ..dtos import TransactionDTO, container_to_dto, transaction_to_dto
from ..interfaces import (
    MoneyContainerRepository,
    MoneyFlowRepository,
    TransactionRepository,
)


@dataclass(frozen=True)
class ListFallbackTransactionsQuery:
    user_id: int
    page: PageRequest


class ListFallbackTransactionsQueryHandler:
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

    async def handle(
        self, query: ListFallbackTransactionsQuery
    ) -> tuple[list[TransactionDTO], int]:
        transactions = await self._transaction_repository.get_user_transactions(
            user_id=query.user_id,
            page=query.page,
        )
        total = await self._transaction_repository.count_user_transactions(query.user_id)

        flows_by_transaction, containers = await asyncio.gather(
            self._money_flow_repository.get_flows_for_transactions(
                [UUID(transaction.unique_id) for transaction in transactions]
            ),
            self._container_repository.resolve_many(
                [transaction.container_id for transaction in transactions],
                user_id=query.user_id,
            ),
        )
        container_dtos = {
            str(container_id): container_to_dto(reference)
            for container_id, reference in containers.items()
        }

        return (
            [
                transaction_to_dto(
                    TransactionAggregate(
                        transaction_entity=transaction,
                        flows=flows_by_transaction.get(UUID(transaction.unique_id), []),
                    ),
                    container_dtos[str(transaction.container_id)],
                )
                for transaction in transactions
            ],
            total,
        )
