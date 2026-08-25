from typing import Protocol
from uuid import UUID

from data_write_core.domain.aggregates import MoneyContainerAggregate

from ..dtos import MoneyContainerDTO, container_to_dto


class ContainerAggregateLoader(Protocol):
    async def load_container_aggregate(
        self,
        container_id: UUID,
        user_id: int,
    ) -> MoneyContainerAggregate: ...


class LoadedContainers:
    def __init__(self, loader: ContainerAggregateLoader, user_id: int) -> None:
        self._loader = loader
        self._user_id = user_id
        self._aggregates: dict[str, MoneyContainerAggregate] = {}

    async def get(self, container_id: UUID) -> MoneyContainerAggregate:
        container_key = str(container_id)
        if container_key not in self._aggregates:
            self._aggregates[container_key] = await self._loader.load_container_aggregate(
                container_id=container_id,
                user_id=self._user_id,
            )

        return self._aggregates[container_key]

    def as_dtos(self) -> dict[str, MoneyContainerDTO]:
        return {
            container_key: container_to_dto(aggregate.as_reference())
            for container_key, aggregate in self._aggregates.items()
        }
