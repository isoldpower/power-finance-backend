from write_service.common.timestamps import to_iso

from data_write_core.application.dtos import CategoryDTO
from data_write_core.domain.value_objects import CategoryReference


def present_category_reference(category: CategoryReference | None) -> dict | None:
    if category is None:
        return None

    return {
        "id": str(category.id),
        "name": category.name,
        "is_global": category.is_global,
    }


class CategoryHttpPresenter:
    @staticmethod
    def present_one(category: CategoryDTO) -> dict:
        return {
            "id": str(category.id),
            "kind": str(category.kind),
            "name": category.name,
            "is_global": category.is_global,
            "created_at": to_iso(category.created_at),
            "updated_at": to_iso(category.updated_at),
            "deleted_at": to_iso(category.deleted_at),
        }

    @staticmethod
    def present_many(categories: list[CategoryDTO]) -> list[dict]:
        return [CategoryHttpPresenter.present_one(category) for category in categories]
