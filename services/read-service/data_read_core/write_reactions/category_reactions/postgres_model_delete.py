from datetime import UTC

from kafka_consumer_py import Effect, EventMessage
from kafka_messages import CategoryDeleted

from data_read_core.shared.postgres_orm import CategoryReadModel

from .._logger_shortcuts import log_category_postgres_deleted
from .._utilities import decode_payload, handle_database_errors


class RemoveCategoryReadModel(Effect):
    async def apply(self, event: EventMessage) -> None:
        payload = decode_payload(event, CategoryDeleted)
        await handle_database_errors(
            self._remove_category,
            payload,
            resource_id=payload.category_id,
        )

    async def _remove_category(self, payload: CategoryDeleted) -> None:
        deleted_at = payload.deleted_at.ToDatetime(tzinfo=UTC)
        await CategoryReadModel.objects.filter(id=payload.category_id).aupdate(
            deleted_at=deleted_at,
            updated_at=deleted_at,
        )

        log_category_postgres_deleted(payload.category_id)
