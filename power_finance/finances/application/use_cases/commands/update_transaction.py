from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from finances.domain.entities import ExpenseCategory

from ..decorators import atomic_evently_command
from ..use_case_base import UseCaseEvently
from ...bootstrap import get_repository_registry
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

        registry = get_repository_registry()
        self._transaction_repository = transaction_repository or registry.transaction_repository

    @atomic_evently_command()
    async def handle(self, command: UpdateTransactionCommand) -> TransactionDTO:
        current_transaction = await self._transaction_repository.get_user_transaction_by_id(
            command.user_id,
            UUID(command.transaction_id),
        )
        current_transaction.migrate_event_collector(self.event_collector)

        current_transaction.update_fields(
            description=command.description,
            category=command.category,
        )
        updated_transaction = await self._transaction_repository.save_transaction(current_transaction)

        return transaction_to_dto(updated_transaction)