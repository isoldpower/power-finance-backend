from uuid import UUID

from data_write_core.domain.entities import CategoryEntity
from data_write_core.domain.events import EventCollector
from data_write_core.domain.value_objects import CategoryKind, CategoryReference
from data_write_core.infrastructure.orm import (
    CategoryModel,
    TransactionCategoryModel,
    WalletCategoryModel,
)


class CategoryMapper:
    @staticmethod
    def to_domain(model: CategoryModel) -> CategoryEntity:
        return CategoryEntity(
            id=model.id,
            kind=CategoryKind(model.kind),
            name=model.name,
            user_id=str(model.user_id) if model.user_id is not None else None,
            is_global=model.is_global,
            created_at=model.created_at,
            updated_at=model.updated_at,
            deleted_at=model.deleted_at,
            event_collector=EventCollector(),
        )

    @staticmethod
    def apply_to_model(model: CategoryModel, entity: CategoryEntity) -> CategoryModel:
        model.id = UUID(entity.unique_id)
        model.kind = str(entity.kind)
        model.name = entity.name
        model.user_id = int(entity.user_id) if entity.user_id is not None else None
        model.is_global = entity.is_global
        model.created_at = entity.created_at
        model.updated_at = entity.updated_at
        model.deleted_at = entity.deleted_at

        return model


def reference_from_model(model: CategoryModel | None) -> CategoryReference | None:
    if model is None:
        return None

    return CategoryReference(id=model.id, name=model.name, is_global=model.is_global)


def transaction_category_model(
    reference: CategoryReference | None,
) -> TransactionCategoryModel | None:
    return _stored_category_model(TransactionCategoryModel, reference)


def wallet_category_model(reference: CategoryReference | None) -> WalletCategoryModel | None:
    return _stored_category_model(WalletCategoryModel, reference)


def _stored_category_model[CategoryModelType: CategoryModel](
    model_type: type[CategoryModelType],
    reference: CategoryReference | None,
) -> CategoryModelType | None:
    if reference is None:
        return None

    stored_category = model_type(
        id=reference.id,
        category_id=reference.id,
        name=reference.name,
        is_global=reference.is_global,
    )
    stored_category._state.adding = False

    return stored_category
