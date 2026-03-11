from dataclasses import dataclass
from uuid import UUID
from django.db import transaction

from finances.infrastructure.repositories import DjangoTransactionRepository

from ..dto_builders import transaction_to_dto
from ..dtos import TransactionDTO
from ..interfaces import TransactionRepository


@dataclass(frozen=True)
class DeleteTransactionCommand:
    transaction_id: str
    user_id: int


class DeleteTransactionCommandHandler:
    transaction_repository: TransactionRepository

    def __init__(
        self,
        transaction_repository: TransactionRepository | None = None
    ):
        self.transaction_repository = transaction_repository or DjangoTransactionRepository()

    @transaction.atomic
    def handle(self, command: DeleteTransactionCommand) -> TransactionDTO:
        deleted_transaction = self.transaction_repository.delete_transaction_by_id(
            UUID(command.transaction_id),
        )

        return transaction_to_dto(deleted_transaction)