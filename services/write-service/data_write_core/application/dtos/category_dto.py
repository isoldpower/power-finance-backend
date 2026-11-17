from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from data_write_core.domain.entities import CategoryEntity
from data_write_core.domain.value_objects import CategoryKind


@dataclass(frozen=True)
class CategoryDTO:
    id: UUID
    kind: CategoryKind
    name: str
    is_global: bool
    created_at: datetime
    updated_at: datetime | None = None
    deleted_at: datetime | None = None


def category_to_dto(category: CategoryEntity) -> CategoryDTO:
    return CategoryDTO(
        id=UUID(category.unique_id),
        kind=category.kind,
        name=category.name,
        is_global=category.is_global,
        created_at=category.created_at,
        updated_at=category.updated_at,
        deleted_at=category.deleted_at,
    )
