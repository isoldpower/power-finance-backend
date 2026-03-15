from abc import ABC, abstractmethod
from uuid import UUID

from finances.domain.entities import Wallet


class WalletSelectorsCollection(ABC):
    @abstractmethod
    def get_ordered_user_wallets(self, user_id: int) -> list[Wallet]:
        raise NotImplementedError()

    @abstractmethod
    def get_single_wallet(self, user_id: int, wallet_id: UUID) -> Wallet:
        raise NotImplementedError()