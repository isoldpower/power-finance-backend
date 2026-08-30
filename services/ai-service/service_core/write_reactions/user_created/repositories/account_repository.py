from abc import ABC, abstractmethod
from collections.abc import Sequence
from datetime import datetime

from ..contracts import AccountRecord, AccountSpec


class AccountRepository(ABC):
    @abstractmethod
    async def ensure(
        self,
        user_id: int,
        accounts: Sequence[AccountSpec],
        now: datetime,
    ) -> list[AccountRecord]:
        """Create the accounts that do not exist yet; report the ones created."""

        raise NotImplementedError()
