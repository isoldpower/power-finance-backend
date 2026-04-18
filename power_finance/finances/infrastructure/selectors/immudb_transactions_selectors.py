from uuid import UUID

from finances.application.interfaces import TransactionSelectorsCollection
from finances.application.bootstrap.state import ImmudbConnection


class ImmudbTransactionSelectorsCollection(TransactionSelectorsCollection):
    def __init__(self, immudb_client: ImmudbConnection):
        self._immudb = immudb_client.client

    async def get_expenses_by_category(self, user_id: int) -> list[dict[str, str]]:
        raise NotImplementedError()

    async def get_monthly_expenditure_and_income(self, user_id: int) -> list[dict[str, str]]:
        raise NotImplementedError()

    async def get_user_transfers_grouped(self, user_id: int) -> list[dict[str, str]]:
        raise NotImplementedError()

    async def get_daily_spending(self, user_id: int) -> list[dict[str, any]]:
        raise NotImplementedError()

    async def get_wallet_transactions(self, wallet_id: UUID) -> list[dict[str, any]]:
        raise NotImplementedError()
