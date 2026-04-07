import logging
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


logger = logging.getLogger(__name__)


class ListOwnedWalletsQueryHandler:
    wallet_repository: WalletRepository

    def __init__(
            self,
            wallet_repository: WalletRepository | None = None
    ):
        registry = get_repository_registry()
        self.wallet_repository = wallet_repository or registry.wallet_repository

    def handle(self, query: ListOwnedWalletsQuery) -> list[WalletDTO]:
        logger.info("ListOwnedWalletsQueryHandler: Handling ListOwnedWalletsQuery for User ID: %s", query.user_id)
        user_wallets = self.wallet_repository.get_user_wallets(query.user_id)

        logger.info("ListOwnedWalletsQueryHandler: Successfully retrieved %d wallets for User ID: %s", len(user_wallets), query.user_id)
        return [
            wallet_to_dto(wallet)
            for wallet in user_wallets
        ]