from abc import ABC, abstractmethod
from uuid import UUID

from finances.domain.entities import Wallet, ResolvedFilterTree


class WalletRepository(ABC):
    @abstractmethod
    async def create_wallet(self, wallet: Wallet) -> Wallet:
        raise NotImplementedError()

    @abstractmethod
    async def get_wallet_by_id(self, wallet_id: UUID) -> Wallet:
        raise NotImplementedError()

    @abstractmethod
    async def get_user_wallet_for_update(self, wallet_id: UUID, user_id: int) -> Wallet:
        raise NotImplementedError()

    @abstractmethod
    async def get_user_wallet_by_id(self, wallet_id: UUID, user_id: int) -> Wallet:
        raise NotImplementedError()

    @abstractmethod
    async def get_ordered_user_wallets(self, user_id: int) -> list[Wallet]:
        raise NotImplementedError()

    @abstractmethod
    async def get_user_wallets(self, user_id: int) -> list[Wallet]:
        raise NotImplementedError()

    @abstractmethod
    async def save_wallet(self, wallet: Wallet) -> Wallet:
        raise NotImplementedError()

    @abstractmethod
    async def soft_delete_wallet(self, wallet_id: UUID, user_id: int) -> Wallet:
        raise NotImplementedError()

    @abstractmethod
    async def list_wallets_with_filters(self, tree: ResolvedFilterTree, user_id: int) -> list[Wallet]:
        raise NotImplementedError()