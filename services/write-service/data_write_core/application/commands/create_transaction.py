from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from ..bootstrap import get_repository_registry
from ..dtos import TransactionDTO, transaction_to_dto, wallet_to_dto
from ..interfaces import TransactionRepository, WalletRepository
from ._command_base import CommandHandlerBase
from ._decorators import atomic_command
from ._loader_mixins import LoadWalletMixin


@dataclass(frozen=True)
class CreateTransactionCommand:
    user_id: int
    source_wallet_id: UUID
    amount: Decimal


class CreateTransactionCommandHandler(CommandHandlerBase, LoadWalletMixin):
    _transaction_repository: TransactionRepository
    _wallet_repository: WalletRepository

    def __init__(
        self,
        transaction_repository: TransactionRepository | None = None,
        wallet_repository: WalletRepository | None = None,
    ) -> None:
        registry = get_repository_registry()
        wallet_repository = wallet_repository or registry.wallet_repository
        transaction_repository = transaction_repository or registry.transaction_repository

        LoadWalletMixin.__init__(self, wallet_repository, transaction_repository)

        self._transaction_repository = transaction_repository
        self._wallet_repository = wallet_repository

    @atomic_command()
    async def handle(self, command: CreateTransactionCommand) -> TransactionDTO:
        wallet_aggregate = await self.load_wallet_aggregate(
            wallet_id=command.source_wallet_id,
            user_id=command.user_id,
        )
        new_transaction = wallet_aggregate.apply_transaction(amount=command.amount)
        await self._transaction_repository.create_transaction(new_transaction)

        await self._publish_events(wallet_aggregate)
        return transaction_to_dto(
            new_transaction,
            wallet_to_dto(
                wallet_aggregate.root,
                balance_amount=wallet_aggregate.balance,
            ),
        )
