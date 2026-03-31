from abc import ABC, abstractmethod
from uuid import UUID

from finances.domain.entities import Transaction, ResolvedFilterTree


class TransactionRepository(ABC):
    @abstractmethod
    def get_user_transactions(self, user_id: int) -> list[Transaction]:
        raise NotImplementedError()

    @abstractmethod
    def get_user_transaction_by_id(self, user_id: int, transaction_id: UUID) -> Transaction:
        raise NotImplementedError()

    @abstractmethod
    def create_transaction(self, transaction: Transaction) -> Transaction:
        raise NotImplementedError()

    @abstractmethod
    def save_transaction(self, transaction: Transaction) -> Transaction:
        raise NotImplementedError()

    @abstractmethod
    def delete_transaction_by_id(self, transaction_id: UUID) -> Transaction:
        raise NotImplementedError()

    @abstractmethod
    def list_transactions_with_filters(self, tree: ResolvedFilterTree, user_id: int) -> list[Transaction]:
        raise NotImplementedError()