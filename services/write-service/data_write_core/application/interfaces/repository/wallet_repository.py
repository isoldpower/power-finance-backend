from abc import ABC, abstractmethod
from uuid import UUID

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
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[WalletEntity]:
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
