from dataclasses import dataclass

from ..dto_builders import transaction_to_dto
from ..dtos import TransactionDTO
from ..interfaces import TransactionRepository

from finances.infrastructure.repositories import DjangoTransactionRepository


@dataclass(frozen=True)
class ListTransactionsQuery:
    user_id: int


class ListTransactionsQueryHandler:
    transaction_repository: TransactionRepository

    def __init__(
        self,
        transaction_repository: TransactionRepository | None = None
    ) -> None:
        self.transaction_repository = transaction_repository or DjangoTransactionRepository()

    def handle(self, query: ListTransactionsQuery) -> list[TransactionDTO]:
        transactions = self.transaction_repository.get_user_transactions(
            query.user_id
        )

        return [transaction_to_dto(transaction) for transaction in transactions]
