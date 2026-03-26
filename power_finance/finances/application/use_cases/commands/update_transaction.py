from dataclasses import dataclass
from typing import Optional
from uuid import UUID
from django.db import transaction

from finances.infrastructure.repositories import DjangoTransactionRepository
from finances.domain.entities import ExpenseCategory

from ..decorators import handle_evently_command
from ..use_case_base import UseCaseEvently
from ...dto_builders import transaction_to_dto
from ...dtos import TransactionDTO
from ...interfaces import TransactionRepository


@dataclass
class UpdateTransactionCommand:
    user_id: int
    transaction_id: str
    description: Optional[str]
    category: Optional[ExpenseCategory]


class UpdateTransactionCommandHandler(UseCaseEvently):
    _transaction_repository: TransactionRepository

    def __init__(
        self,
        transaction_repository: TransactionRepository | None = None,
    ):
        super().__init__()

        self._transaction_repository = transaction_repository or DjangoTransactionRepository()

    @handle_evently_command
    @transaction.atomic
    def handle(self, command: UpdateTransactionCommand) -> TransactionDTO:
        current_transaction = self._transaction_repository.get_user_transaction_by_id(
            command.user_id,
            UUID(command.transaction_id),
        )
        current_transaction.migrate_event_collector(self.event_collector)

        current_transaction.update_fields(
            description=current_transaction.description,
            category=current_transaction.category,
        )
        updated_transaction = self._transaction_repository.save_transaction(current_transaction)

        return transaction_to_dto(updated_transaction)