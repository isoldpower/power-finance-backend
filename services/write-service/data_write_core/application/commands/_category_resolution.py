from typing import Any
from uuid import UUID

from data_write_core.domain.services import assignable_reference
from data_write_core.domain.value_objects import CategoryKind, CategoryReference

from ..bootstrap import get_repository_registry
from ..interfaces import CategoryRepository


class CategoryResolverMixin:
    _category_repository: CategoryRepository | None = None

    def use_category_repository(self, category_repository: CategoryRepository | None) -> None:
        self._category_repository = category_repository

    async def resolve_category(
        self,
        category_id: UUID | None,
        user_id: int,
        kind: CategoryKind,
    ) -> CategoryReference | None:
        if category_id is None:
            return None

        category = await self._categories().get_visible_category(category_id, user_id)
        return assignable_reference(category, kind)

    async def resolve_category_change(
        self,
        category_id: UUID | None | object,
        user_id: int,
        kind: CategoryKind,
        unchanged: object,
    ) -> CategoryReference | None | object:
        if category_id is unchanged:
            return unchanged
        if category_id is not None and not isinstance(category_id, UUID):
            raise TypeError(f"category_id must be a UUID or None, got {category_id!r}")

        return await self.resolve_category(category_id, user_id, kind)

    def _categories(self) -> CategoryRepository:
        if self._category_repository is None:
            self._category_repository = get_repository_registry().category_repository

        return self._category_repository


def category_event_fields(category: CategoryReference | None) -> dict[str, Any]:
    if category is None:
        return {"category": "", "category_id": ""}

    return {"category": category.name, "category_id": str(category.id)}
