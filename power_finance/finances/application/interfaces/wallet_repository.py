from abc import ABC, abstractmethod
from uuid import UUID

from finances.domain.entities.wallet import Wallet


class WalletRepository(ABC):
    @abstractmethod
    def create_wallet(self, wallet: Wallet) -> Wallet:
        raise NotImplementedError

    @abstractmethod
    def get_wallet_by_id(self, wallet_id: UUID) -> Wallet:
        raise NotImplementedError

    @abstractmethod
    def get_user_wallet_for_update(self, wallet_id: UUID, user_id: int) -> Wallet:
        raise NotImplementedError

    @abstractmethod
    def get_user_wallet_by_id(self, wallet_id: UUID, user_id: int) -> Wallet:
        raise NotImplementedError

    @abstractmethod
    def get_ordered_user_wallets(self, user_id: int) -> list[Wallet]:
        raise NotImplementedError()

    @abstractmethod
    def get_user_wallets(self, user_id: int) -> list[Wallet]:
        raise NotImplementedError

    @abstractmethod
    def save_wallet(self, wallet: Wallet) -> Wallet:
        raise NotImplementedError

    @abstractmethod
    def soft_delete_wallet(self, wallet_id: UUID, user_id: int) -> Wallet:
        raise NotImplementedError