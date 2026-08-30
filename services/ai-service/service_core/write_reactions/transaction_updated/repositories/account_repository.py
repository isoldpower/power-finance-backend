from abc import ABC, abstractmethod
from collections.abc import Collection, Sequence
from datetime import datetime
from uuid import UUID

from ..contracts import AccountSpec, BalanceChange


class AccountRepository(ABC):
    @abstractmethod
    async def resolve(self, user_id: int, accounts: Sequence[AccountSpec]) -> list[UUID]:
        raise NotImplementedError()

    @abstractmethod
    async def recompute_balances(
        self, account_ids: Collection[UUID], now: datetime
    ) -> list[BalanceChange]:
        raise NotImplementedError()
