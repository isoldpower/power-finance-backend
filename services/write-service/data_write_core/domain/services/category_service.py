from uuid import UUID

from ..entities import CategoryEntity
from ..exceptions import (
    CategoryKindMismatchError,
    CategoryNotFoundError,
    GlobalCategoryImmutableError,
)
from ..value_objects import CategoryKind, CategoryReference


def ensure_category_editable(category: CategoryEntity) -> None:
    if category.is_global:
        raise GlobalCategoryImmutableError(UUID(category.unique_id))


def assignable_reference(
    category: CategoryEntity,
    expected_kind: CategoryKind,
) -> CategoryReference:
    category_id = UUID(category.unique_id)
    if category.deleted_at is not None:
        raise CategoryNotFoundError(category_id)
    if category.kind is not expected_kind:
        raise CategoryKindMismatchError(category_id, str(expected_kind), str(category.kind))

    return category.as_reference()
