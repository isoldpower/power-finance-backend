import asyncio
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from ..use_case_base import UseCaseEvently
from ..decorators import atomic_evently_command
from ...bootstrap import get_repository_registry
from ...dto_builders import transaction_to_dto, wallet_to_dto
from ...dtos import TransactionDTO
from ...interfaces import TransactionRepository, WalletRepository


@dataclass(frozen=True)
class CreateTransactionCommand:
    user_id: int
    source_wallet_id: UUID
    amount: Decimal


class CreateTransactionCommandHandler(UseCaseEvently):
    _transaction_repository: TransactionRepository
    _wallet_repository: WalletRepository

    def __init__(
        self,
        transaction_repository: TransactionRepository | None = None,
        wallet_repository: WalletRepository | None = None,
    ):
        super().__init__()
        registry = get_repository_registry()
        self._transaction_repository = transaction_repository or registry.transaction_repository
        self._wallet_repository = wallet_repository or registry.wallet_repository

    @atomic_evently_command()
    async def handle(self, command: CreateTransactionCommand) -> TransactionDTO:
        wallet, transactions = await asyncio.gather(*[
            self._wallet_repository.get_user_wallet_by_id(
                wallet_id=command.source_wallet_id,
                user_id=command.user_id,
            ),
            self._transaction_repository.get_wallet_transactions(command.source_wallet_id),
        ])
        wallet.transactions = transactions
        new_transaction = wallet.apply_transaction(
            user_id=command.user_id,
            amount=command.amount,
        )
        new_transaction.migrate_event_collector(self.event_collector)
        await self._transaction_repository.create_transaction(new_transaction)

        return transaction_to_dto(new_transaction, wallet_to_dto(wallet))
