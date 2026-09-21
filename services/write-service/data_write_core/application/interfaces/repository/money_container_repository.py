from abc import ABC, abstractmethod
from uuid import UUID

from data_write_core.domain.value_objects import MoneyContainerRef


class MoneyContainerRepository(ABC):
    @abstractmethod
    async def resolve(
        self,
        container_id: UUID,
        user_id: int,
    ) -> MoneyContainerRef:
        raise NotImplementedError()

    @abstractmethod
    async def resolve_many(
        self,
        container_ids: list[UUID],
        user_id: int,
    ) -> dict[UUID, MoneyContainerRef]:
        raise NotImplementedError()
