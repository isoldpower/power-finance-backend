from datetime import UTC, datetime
from uuid import UUID, uuid4, uuid5

from data_read_core.shared.postgres_orm import CategoryReadModel

GLOBAL_CATEGORY_NAMESPACE = UUID("7d3f0f0e-2c1b-4c55-9a43-6f1b9c2e8a10")
FIXTURE_CREATED_AT = datetime(2026, 1, 1, tzinfo=UTC)


def global_category_id(kind: str, name: str) -> UUID:
    return uuid5(GLOBAL_CATEGORY_NAMESPACE, f"{kind}:{name.casefold()}")


async def global_category(kind: str, name: str) -> CategoryReadModel:
    category, _ = await CategoryReadModel.objects.aget_or_create(
        id=global_category_id(kind, name),
        defaults={
            "kind": kind,
            "name": name,
            "is_global": True,
            "user_id": None,
            "created_at": FIXTURE_CREATED_AT,
        },
    )
    return category


async def owned_category(user_id: int, kind: str, name: str) -> CategoryReadModel:
    category, _ = await CategoryReadModel.objects.aget_or_create(
        user_id=user_id,
        kind=kind,
        name=name,
        defaults={"id": uuid4(), "is_global": False, "created_at": FIXTURE_CREATED_AT},
    )
    return category


def category_payload(category: CategoryReadModel | None) -> dict | None:
    if category is None:
        return None

    return {"id": str(category.id), "name": category.name, "is_global": category.is_global}
