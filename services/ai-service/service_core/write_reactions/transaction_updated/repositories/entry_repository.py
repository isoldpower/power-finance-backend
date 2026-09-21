from abc import ABC, abstractmethod
from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from ..contracts import BookedLeg, ReplacedPostings


class EntryRepository(ABC):
    @abstractmethod
    async def accounts_behind(self, transaction_id: UUID) -> set[UUID]:
        raise NotImplementedError()

    @abstractmethod
    async def replace_for_transaction(
        self,
        transaction_id: UUID,
        user_id: int,
        legs: Sequence[BookedLeg],
        now: datetime,
    ) -> ReplacedPostings:
        raise NotImplementedError()
