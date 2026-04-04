from dataclasses import dataclass
from typing import Optional

from ...bootstrap import get_repository_registry
from ...dto_builders import wallet_to_dto
from ...dtos import WalletDTO
from ...interfaces import WalletRepository


@dataclass(frozen=True)
class ListOwnedWalletsQuery:
    user_id: int
    limit: Optional[int]
    offset: Optional[int]


class ListOwnedWalletsQueryHandler:
    wallet_repository: WalletRepository

    def __init__(
            self,
            wallet_repository: WalletRepository | None = None
    ):
        registry = get_repository_registry()
        self.wallet_repository = wallet_repository or registry.wallet_repository

    def handle(self, query: ListOwnedWalletsQuery) -> list[WalletDTO]:
        user_wallets = self.wallet_repository.get_user_wallets(query.user_id)

        return [
            wallet_to_dto(wallet)
            for wallet in user_wallets
        ]