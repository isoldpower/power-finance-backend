from abc import ABC, abstractmethod
from uuid import UUID


class TransactionSelectorsCollection(ABC):
    @abstractmethod
    def get_expenses_by_category(self, user_id: int) -> list[dict[str, str]]:
        raise NotImplementedError()

    @abstractmethod
    def get_monthly_expenditure_and_income(self, user_id: int) -> list[dict[str, str]]:
        raise NotImplementedError()

    @abstractmethod
    def get_user_transfers_grouped(self, user_id: int) -> list[dict[str, str]]:
        raise NotImplementedError()

    @abstractmethod
    def get_daily_spending(self, user_id: int) -> list[dict[str, any]]:
        raise NotImplementedError()

    @abstractmethod
    def get_wallet_transactions(self, wallet_id: UUID) -> list[dict[str, any]]:
        raise NotImplementedError()
