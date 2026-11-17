from datetime import UTC

from kafka_consumer_py import Effect, EventMessage
from kafka_messages import CategoryUpdated

from data_read_core.shared.postgres_orm import CategoryReadModel

from .._logger_shortcuts import log_category_postgres_renamed
from .._utilities import decode_payload, handle_database_errors


class RenameCategoryReadModel(Effect):
    async def apply(self, event: EventMessage) -> None:
        payload = decode_payload(event, CategoryUpdated)
        await handle_database_errors(
            self._rename_category,
            payload,
            resource_id=payload.category_id,
        )

    async def _rename_category(self, payload: CategoryUpdated) -> None:
        await CategoryReadModel.objects.filter(id=payload.category_id).aupdate(
            name=payload.new_name,
            updated_at=payload.updated_at.ToDatetime(tzinfo=UTC),
        )

        log_category_postgres_renamed(payload.category_id, payload.new_name)
