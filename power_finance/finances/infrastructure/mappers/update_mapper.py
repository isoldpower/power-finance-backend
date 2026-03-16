from typing import Generic, TypeVar

from django.db import models


TModel = TypeVar('TModel', bound=models.Model)
TEntity = TypeVar('TEntity')

class UpdateMapper(Generic[TModel, TEntity]):
    @staticmethod
    def _get_initial_key(path: str):
        return path.split(".")[0]

    @staticmethod
    def _resolve_attr(obj, path: str, replace: bool = False):
        current = obj
        for part in path.split("."):
            current = getattr(current, part)
            if current is None and replace is False:
                return None

        return current

    @staticmethod
    def update_model(
            model: TModel,
            entity: TEntity,
            update_fields: list[tuple[str, str]],
            replace: bool = False
    ) -> TModel:
        for model_field, entity_field in update_fields:
            entity_value = UpdateMapper._resolve_attr(entity, entity_field)
            model_value = getattr(model, model_field)

            if (entity_value is not None or replace) and model_value != entity_value:
                setattr(model, model_field, entity_value)

        return model

    @staticmethod
    def get_changed_fields(
            model: TModel,
            entity: TEntity,
            update_fields: list[tuple[str, str]],
            updated_list=None
    ) -> list[str]:
        if updated_list is None:
            updated_list = []

        for model_field, entity_field in update_fields:
            entity_value = UpdateMapper._resolve_attr(entity, entity_field)
            model_value = getattr(model, model_field)

            if model_value != entity_value:
                updated_list.append(model_field)

        return updated_list