from datetime import UTC

from kafka_consumer_py import Effect, EventMessage
from kafka_messages import CategoryCreated

from data_read_core.shared.postgres_orm import CategoryReadModel

from .._logger_shortcuts import log_category_postgres_created
from .._utilities import decode_payload, handle_database_errors


class CreateCategoryReadModel(Effect):
    async def apply(self, event: EventMessage) -> None:
        payload = decode_payload(event, CategoryCreated)
        await handle_database_errors(
            self._create_category,
            payload,
            resource_id=payload.category_id,
        )

    async def _create_category(self, payload: CategoryCreated) -> None:
        await CategoryReadModel.objects.aupdate_or_create(
            id=payload.category_id,
            defaults={
                "user_id": payload.user_id,
                "kind": payload.kind,
                "name": payload.name,
                "is_global": False,
                "created_at": payload.created_at.ToDatetime(tzinfo=UTC),
                "updated_at": None,
                "deleted_at": None,
            },
        )

        log_category_postgres_created(payload.category_id)
