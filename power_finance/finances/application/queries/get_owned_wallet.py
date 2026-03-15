from dataclasses import dataclass
from uuid import UUID

from finances.infrastructure.repositories import DjangoWalletRepository

from ..dto_builders import wallet_to_dto
from ..dtos import WalletDTO
from ..interfaces import WalletRepository


@dataclass
class GetOwnedWalletQuery:
    user_id: int
    wallet_id: str


class GetOwnedWalletQueryHandler:
    wallet_repository: WalletRepository

    def __init__(
        self,
        wallet_repository: WalletRepository | None = None,
    ):
        self.wallet_repository = wallet_repository or DjangoWalletRepository()

    def handle(self, query: GetOwnedWalletQuery) -> WalletDTO:
        requested_wallet = self.wallet_repository.get_user_wallet_by_id(
            UUID(query.wallet_id),
            query.user_id
        )

        return wallet_to_dto(requested_wallet)