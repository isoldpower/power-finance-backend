import asyncio
from dataclasses import dataclass
from uuid import UUID

from finances.domain.builders import WalletBuilder

from ..use_case_base import UseCaseEvently
from ..decorators import atomic_evently_command
from ...bootstrap import get_repository_registry
from ...dto_builders import wallet_to_dto
from ...dtos import WalletDTO
from ...interfaces import WalletRepository, TransactionRepository


@dataclass(frozen=True)
class SoftDeleteWalletCommand:
    wallet_id: str
    user_id: int


class SoftDeleteWalletCommandHandler(UseCaseEvently):
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

    @atomic_evently_command()
    async def handle(self, command: SoftDeleteWalletCommand) -> WalletDTO:
        wallet_id = UUID(command.wallet_id)
        wallet, checkpoint = await asyncio.gather(
            self.wallet_repository.soft_delete_wallet(wallet_id, command.user_id),
            self.transaction_repository.get_checkpoint(wallet_id),
        )
        wallet = (
            WalletBuilder(wallet)
                .set_checkpoint(checkpoint)
                .set_transactions(await self.transaction_repository.get_unsettled_transactions(
                    wallet_id, checkpoint.settled_at if checkpoint else None
                ))
                .build_wallet()
        )
        return wallet_to_dto(wallet)
