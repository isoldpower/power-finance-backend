from collections.abc import Iterable
from typing import TypedDict

from data_read_core.shared.postgres_orm import CategoryReadModel


class CategoryReferencePayload(TypedDict):
    id: str
    name: str
    is_global: bool


def category_reference_of(category: CategoryReadModel | None) -> CategoryReferencePayload | None:
    if category is None:
        return None

    return _reference_of(category)


async def fetch_category_references(
    category_identifiers: Iterable[str | None],
) -> dict[str, CategoryReferencePayload]:
    wanted_identifiers = {identifier for identifier in category_identifiers if identifier}
    if not wanted_identifiers:
        return {}

    return {
        str(category.id): _reference_of(category)
        async for category in CategoryReadModel.objects.filter(id__in=wanted_identifiers)
    }


def _reference_of(category: CategoryReadModel) -> CategoryReferencePayload:
    return CategoryReferencePayload(
        id=str(category.id),
        name=category.name,
        is_global=category.is_global,
    )
