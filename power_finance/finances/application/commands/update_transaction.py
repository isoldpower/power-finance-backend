from dataclasses import dataclass
from typing import Optional
from uuid import UUID
from django.db import transaction

from finances.infrastructure.repositories import DjangoTransactionRepository
from finances.domain.entities import TransactionType, ExpenseCategory, Transaction

from ..dto_builders import transaction_to_dto
from ..dtos import TransactionDTO
from ..interfaces import TransactionRepository


@dataclass
class UpdateTransactionCommand:
    user_id: int
    transaction_id: str
    description: Optional[str]
    type: TransactionType
    category: Optional[ExpenseCategory]


class UpdateTransactionCommandHandler:
    transaction_repository: TransactionRepository

    def __init__(
        self,
        transaction_repository: TransactionRepository | None = None,
    ):
        self.transaction_repository = transaction_repository or DjangoTransactionRepository()

    def _update_fields(self, current_transaction: Transaction, command: UpdateTransactionCommand) -> Transaction:
        if command.category is not None:
            current_transaction.category = command.category
        if command.type is not None:
            current_transaction.type = command.type
        if command.description is not None:
            current_transaction.description = command.description

        return self.transaction_repository.save_transaction(current_transaction)


    @transaction.atomic
    def handle(self, command: UpdateTransactionCommand) -> TransactionDTO:
        current_transaction = self.transaction_repository.get_user_transaction_by_id(
            command.user_id,
            UUID(command.transaction_id),
        )
        updated_transaction = self._update_fields(current_transaction, command)

        return transaction_to_dto(updated_transaction)