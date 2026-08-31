from kafka_consumer_py import Effect, EventMessage
from kafka_messages import AccountPostingDeleted

from data_read_core.shared.postgres_orm import AccountPostingReadModel

from .._logger_shortcuts import log_posting_postgres_removed
from .._utilities import decode_payload, handle_database_errors


class RemoveAccountPostingReadModel(Effect):
    async def apply(self, event: EventMessage) -> None:
        payload = decode_payload(event, AccountPostingDeleted)
        await handle_database_errors(
            self._remove_posting,
            payload,
            resource_id=payload.posting_id,
        )

    async def _remove_posting(self, payload: AccountPostingDeleted) -> None:
        removed_count, _ = await AccountPostingReadModel.objects.filter(
            id=payload.posting_id,
        ).adelete()

        log_posting_postgres_removed(payload.posting_id, removed_count)
