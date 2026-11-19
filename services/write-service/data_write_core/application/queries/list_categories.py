import asyncio
from dataclasses import dataclass

from write_service.common.pagination import PageRequest

from data_write_core.domain.value_objects import CategoryKind

from ..bootstrap import get_repository_registry
from ..dtos import CategoryDTO, category_to_dto
from ..interfaces import CategoryRepository


@dataclass(frozen=True)
class ListFallbackCategoriesQuery:
    user_id: int
    page: PageRequest
    kind: CategoryKind | None = None


class ListFallbackCategoriesQueryHandler:
    def __init__(self, category_repository: CategoryRepository | None = None) -> None:
        self._category_repository = (
            category_repository or get_repository_registry().category_repository
        )

    async def handle(self, query: ListFallbackCategoriesQuery) -> tuple[list[CategoryDTO], int]:
        categories, total = await asyncio.gather(
            self._category_repository.get_visible_categories(
                user_id=query.user_id,
                kind=query.kind,
                page=query.page,
            ),
            self._category_repository.count_visible_categories(query.user_id, query.kind),
        )

        return [category_to_dto(category) for category in categories], total
