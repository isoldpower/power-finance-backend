from abc import ABC, abstractmethod
from uuid import UUID

from finances.domain.entities.transaction import Transaction


class TransactionRepository(ABC):
    @abstractmethod
    def get_user_transactions(self, user_id: UUID) -> list[Transaction]:
        raise NotImplementedError