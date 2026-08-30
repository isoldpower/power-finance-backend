from abc import ABC, abstractmethod
from collections.abc import Collection
from datetime import datetime
from uuid import UUID

from ..contracts import BalanceChange


class AccountRepository(ABC):
    @abstractmethod
    async def recompute_balances(
        self, account_ids: Collection[UUID], now: datetime
    ) -> list[BalanceChange]:
        """Re-derive each account's balance from its entries; report the moves."""

        raise NotImplementedError()
