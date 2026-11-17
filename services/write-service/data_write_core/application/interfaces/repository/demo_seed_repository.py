from abc import ABC, abstractmethod
from collections.abc import Collection
from uuid import UUID


class DemoSeedRepository(ABC):
    @abstractmethod
    async def is_seed_completed(self, user_id: int) -> bool:
        raise NotImplementedError()

    @abstractmethod
    async def mark_seed_completed(self, user_id: int) -> None:
        raise NotImplementedError()

    @abstractmethod
    async def find_existing_seed_items(
        self,
        user_id: int,
        candidate_item_ids: Collection[UUID],
    ) -> set[UUID]:
        raise NotImplementedError()
