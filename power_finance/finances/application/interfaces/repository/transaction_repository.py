from abc import ABC, abstractmethod
from uuid import UUID

from finances.domain.entities import Transaction, ResolvedFilterTree, BalanceCheckpoint


class TransactionRepository(ABC):
    @abstractmethod
    async def get_user_transactions(self, user_id: int) -> list[Transaction]:
        raise NotImplementedError()

    @abstractmethod
    async def get_user_transaction_by_id(self, user_id: int, transaction_id: UUID) -> Transaction:
        raise NotImplementedError()

    @abstractmethod
    async def create_transaction(self, transaction: Transaction) -> Transaction:
        raise NotImplementedError()

    @abstractmethod
    async def delete_transaction_by_id(self, user_id: int, transaction_id: UUID) -> Transaction:
        raise NotImplementedError()

    @abstractmethod
    async def list_transactions_with_filters(self, tree: ResolvedFilterTree, user_id: int) -> list[Transaction]:
        raise NotImplementedError()

    @abstractmethod
    async def get_cancelling_transaction(self, transaction_id: UUID) -> Transaction | None:
        raise NotImplementedError()

    @abstractmethod
    async def get_unsettled_transactions(self, wallet_id: UUID, settled_at: str | None = None) -> list[Transaction]:
        raise NotImplementedError()

    @abstractmethod
    async def get_checkpoint(self, wallet_id: UUID) -> BalanceCheckpoint | None:
        raise NotImplementedError()

    @abstractmethod
    async def save_checkpoint(self, checkpoint: BalanceCheckpoint) -> None:
        raise NotImplementedError()
