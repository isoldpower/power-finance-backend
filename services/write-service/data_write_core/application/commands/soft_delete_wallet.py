from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from ..bootstrap import get_repository_registry
from ..dtos import WalletDTO, wallet_to_dto
from ..interfaces import TransactionRepository, WalletRepository
from ._command_base import CommandHandlerBase
from ._decorators import atomic_command
from ._loader_mixins import LoadWalletMixin


@dataclass(frozen=True)
class SoftDeleteWalletCommand:
    user_id: int
    wallet_id: UUID


class SoftDeleteWalletCommandHandler(CommandHandlerBase, LoadWalletMixin):
    _wallet_repository: WalletRepository
    _transaction_repository: TransactionRepository

    def __init__(
        self,
        wallet_repository: WalletRepository | None = None,
        transaction_repository: TransactionRepository | None = None,
    ) -> None:
        registry = get_repository_registry()
        wallet_repository = wallet_repository or registry.wallet_repository
        transaction_repository = transaction_repository or registry.transaction_repository

        LoadWalletMixin.__init__(self, wallet_repository, transaction_repository)

        self._wallet_repository = wallet_repository
        self._transaction_repository = transaction_repository

    @atomic_command()
    async def handle(self, command: SoftDeleteWalletCommand) -> WalletDTO:
        wallet_aggregate = await self.load_wallet_aggregate(
            wallet_id=command.wallet_id,
            user_id=command.user_id,
        )
        wallet_aggregate.soft_delete(now=datetime.now())
        saved_wallet = await self._wallet_repository.save_wallet(wallet_aggregate.root)

        await self._publish_events(wallet_aggregate)
        return wallet_to_dto(saved_wallet, balance_amount=wallet_aggregate.balance)
