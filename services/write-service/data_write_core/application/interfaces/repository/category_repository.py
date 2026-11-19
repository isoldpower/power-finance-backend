from abc import ABC, abstractmethod
from uuid import UUID

from write_service.common.pagination import PageRequest

from data_write_core.domain.entities import CategoryEntity
from data_write_core.domain.value_objects import CategoryKind


class CategoryRepository(ABC):
    @abstractmethod
    async def get_visible_category(self, category_id: UUID, user_id: int) -> CategoryEntity:
        raise NotImplementedError()

    @abstractmethod
    async def get_visible_categories(
        self,
        user_id: int,
        kind: CategoryKind | None = None,
        page: PageRequest | None = None,
    ) -> list[CategoryEntity]:
        raise NotImplementedError()

    @abstractmethod
    async def count_visible_categories(self, user_id: int, kind: CategoryKind | None = None) -> int:
        raise NotImplementedError()

    @abstractmethod
    async def is_name_taken(
        self,
        user_id: int,
        kind: CategoryKind,
        name: str,
        excluding_category_id: UUID | None = None,
    ) -> bool:
        raise NotImplementedError()

    @abstractmethod
    async def create_category(self, category: CategoryEntity) -> CategoryEntity:
        raise NotImplementedError()

    @abstractmethod
    async def save_category(self, category: CategoryEntity) -> CategoryEntity:
        raise NotImplementedError()

    @abstractmethod
    async def hard_delete_category(self, category_id: UUID) -> None:
        raise NotImplementedError()
