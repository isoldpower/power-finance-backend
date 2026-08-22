from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID

from write_service.common.pagination import PageRequest

from data_write_core.domain.entities import TransactionEntity


class TransactionRepository(ABC):
    @abstractmethod
    async def create_transaction(self, transaction: TransactionEntity) -> TransactionEntity:
        raise NotImplementedError()

    @abstractmethod
    async def save_transaction(self, transaction: TransactionEntity) -> TransactionEntity:
        raise NotImplementedError()

    @abstractmethod
    async def get_user_transaction_by_id(
        self,
        transaction_id: UUID,
        user_id: int,
    ) -> TransactionEntity:
        raise NotImplementedError()

    @abstractmethod
    async def get_user_transactions(
        self,
        user_id: int,
        page: PageRequest | None = None,
    ) -> list[TransactionEntity]:
        raise NotImplementedError()

    @abstractmethod
    async def count_user_transactions(self, user_id: int) -> int:
        raise NotImplementedError()

    @abstractmethod
    async def hard_delete_transaction(self, transaction_id: UUID) -> None:
        raise NotImplementedError()

    @abstractmethod
    async def create_chain(self, chain_id: UUID, user_id: int, created_at: datetime) -> None:
        raise NotImplementedError()

    @abstractmethod
    async def get_chain_transactions(
        self,
        chain_id: UUID,
        user_id: int,
    ) -> list[TransactionEntity]:
        raise NotImplementedError()

    @abstractmethod
    async def hard_delete_chain(self, chain_id: UUID) -> None:
        raise NotImplementedError()
