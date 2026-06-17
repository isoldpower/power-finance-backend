from abc import ABC, abstractmethod
from uuid import UUID

from data_write_core.domain.entities import BalanceCheckpointEntity, TransactionEntity


class TransactionRepository(ABC):
    @abstractmethod
    async def get_user_transactions(
        self,
        user_id: int,
    ) -> list[TransactionEntity]:
        raise NotImplementedError()

    @abstractmethod
    async def get_user_transaction_by_id(
        self,
        user_id: int,
        transaction_id: UUID,
    ) -> TransactionEntity:
        raise NotImplementedError()

    @abstractmethod
    async def create_transaction(
        self,
        transaction: TransactionEntity,
    ) -> TransactionEntity:
        raise NotImplementedError()

    @abstractmethod
    async def delete_transaction_by_id(
        self,
        user_id: int,
        transaction_id: UUID,
    ) -> TransactionEntity:
        raise NotImplementedError()

    @abstractmethod
    async def get_cancelling_transaction(
        self,
        transaction_id: UUID,
    ) -> TransactionEntity | None:
        raise NotImplementedError()

    @abstractmethod
    async def get_adjusting_transaction(
        self,
        transaction_id: UUID,
    ) -> TransactionEntity | None:
        raise NotImplementedError()

    @abstractmethod
    async def get_unsettled_transactions(
        self,
        wallet_id: UUID,
        settled_at: str | None = None,
    ) -> list[TransactionEntity]:
        raise NotImplementedError()

    @abstractmethod
    async def get_checkpoint(
        self,
        wallet_id: UUID,
    ) -> BalanceCheckpointEntity | None:
        raise NotImplementedError()

    @abstractmethod
    async def save_checkpoint(
        self,
        checkpoint: BalanceCheckpointEntity,
    ) -> None:
        raise NotImplementedError()
