from dataclasses import dataclass

from finances.infrastructure.repositories import DjangoTransactionRepository

from ...dto_builders import transaction_to_plain_dto
from ...dtos import TransactionPlainDTO
from ...interfaces import TransactionRepository


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

    def handle(self, query: ListTransactionsQuery) -> list[TransactionPlainDTO]:
        transactions = self.transaction_repository.get_user_transactions(query.user_id)

        return [transaction_to_plain_dto(transaction) for transaction in transactions]
