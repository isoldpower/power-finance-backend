import logging
from dataclasses import dataclass

from ...bootstrap import get_repository_registry
from ...dto_builders import transaction_to_plain_dto
from ...dtos import TransactionPlainDTO
from ...interfaces import TransactionRepository


@dataclass(frozen=True)
class ListTransactionsQuery:
    user_id: int


logger = logging.getLogger(__name__)


class ListTransactionsQueryHandler:
    transaction_repository: TransactionRepository

    def __init__(
        self,
        transaction_repository: TransactionRepository | None = None
    ) -> None:
        registry = get_repository_registry()
        self.transaction_repository = transaction_repository or registry.transaction_repository

    async def handle(self, query: ListTransactionsQuery) -> list[TransactionPlainDTO]:
        logger.info("ListTransactionsQueryHandler: Handling ListTransactionsQuery for User ID: %s", query.user_id)
        user_transactions = await self.transaction_repository.get_user_transactions(query.user_id)

        logger.info("ListTransactionsQueryHandler: Successfully retrieved %d transactions for User ID: %s", len(user_transactions), query.user_id)
        return [
            transaction_to_plain_dto(transaction)
            for transaction in user_transactions
        ]
