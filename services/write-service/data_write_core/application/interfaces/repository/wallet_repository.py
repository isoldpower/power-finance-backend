from abc import ABC, abstractmethod
from uuid import UUID

from write_service.common.pagination import PageRequest

from data_write_core.domain.entities import WalletEntity


class WalletRepository(ABC):
    @abstractmethod
    async def create_wallet(self, wallet: WalletEntity) -> WalletEntity:
        raise NotImplementedError()

    @abstractmethod
    async def get_wallet_by_id(self, wallet_id: UUID) -> WalletEntity:
        raise NotImplementedError()

    @abstractmethod
    async def get_user_wallet_by_id(self, wallet_id: UUID, user_id: int) -> WalletEntity:
        raise NotImplementedError()

    @abstractmethod
    async def get_user_wallets(
        self,
        user_id: int,
        page: PageRequest | None = None,
    ) -> list[WalletEntity]:
        """One page of rows, including the lookahead row. Newest first."""
        raise NotImplementedError()

    @abstractmethod
    async def count_user_wallets(self, user_id: int) -> int:
        raise NotImplementedError()

    @abstractmethod
    async def get_user_wallet_for_update(
        self,
        wallet_id: UUID,
        user_id: int,
    ) -> WalletEntity:
        raise NotImplementedError()

    @abstractmethod
    async def save_wallet(self, wallet: WalletEntity) -> WalletEntity:
        raise NotImplementedError()

    @abstractmethod
    async def hard_delete_wallet(self, wallet_id: UUID) -> None:
        raise NotImplementedError()
