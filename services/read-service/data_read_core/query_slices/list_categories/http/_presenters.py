from ..dtos import CategoryDTO


def present_one(category: CategoryDTO) -> dict:
    return {
        "id": category.id,
        "kind": category.kind,
        "name": category.name,
        "is_global": category.is_global,
        "created_at": category.created_at,
        "updated_at": category.updated_at,
        "deleted_at": category.deleted_at,
    }


def present_many(categories: list[CategoryDTO]) -> list[dict]:
    return [present_one(category) for category in categories]
