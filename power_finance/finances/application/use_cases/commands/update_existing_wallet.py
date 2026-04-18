import asyncio
from dataclasses import dataclass
from uuid import UUID

from finances.domain.entities import Wallet

from ..use_case_base import UseCaseEvently
from ..decorators import atomic_evently_command
from ...bootstrap import get_repository_registry
from ...dto_builders import wallet_to_dto
from ...dtos import WalletDTO
from ...interfaces import WalletRepository, TransactionRepository


@dataclass
class UpdateExistingWalletCommand:
    wallet_id: str
    user_id: int
    name: str | None = None


class UpdateExistingWalletCommandHandler(UseCaseEvently):
    wallet_repository: WalletRepository
    transaction_repository: TransactionRepository

    def __init__(
        self,
        wallet_repository: WalletRepository | None = None,
        transaction_repository: TransactionRepository | None = None,
    ):
        super().__init__()
        registry = get_repository_registry()
        self.wallet_repository = wallet_repository or registry.wallet_repository
        self.transaction_repository = transaction_repository or registry.transaction_repository

    async def _update_fields(self, wallet: Wallet, command: UpdateExistingWalletCommand) -> Wallet:
        if command.name is not None:
            wallet.name = command.name

        return await self.wallet_repository.save_wallet(wallet)

    @atomic_evently_command()
    async def handle(self, command: UpdateExistingWalletCommand) -> WalletDTO:
        wallet_id = UUID(command.wallet_id)
        wallet, transactions = await asyncio.gather(*[
            self.wallet_repository.get_user_wallet_by_id(wallet_id, command.user_id),
            self.transaction_repository.get_wallet_transactions(wallet_id),
        ])
        wallet.transactions = transactions
        updated_wallet = await self._update_fields(wallet, command)

        return wallet_to_dto(updated_wallet)
