from dataclasses import dataclass
from uuid import UUID
from django.db import transaction

from ...bootstrap import get_repository_registry
from ...dto_builders import wallet_to_dto
from ...dtos import WalletDTO
from ...interfaces import WalletRepository


@dataclass(frozen=True)
class SoftDeleteWalletCommand:
    wallet_id: str
    user_id: int


class SoftDeleteWalletCommandHandler:
    wallet_repository: WalletRepository

    def __init__(
        self,
        wallet_repository: WalletRepository | None = None
    ):
        registry = get_repository_registry()
        self.wallet_repository = wallet_repository or registry.wallet_repository

    @transaction.atomic
    def handle(self, command: SoftDeleteWalletCommand) -> WalletDTO:
        wallet = self.wallet_repository.soft_delete_wallet(
            UUID(command.wallet_id),
            command.user_id
        )

        return wallet_to_dto(wallet)