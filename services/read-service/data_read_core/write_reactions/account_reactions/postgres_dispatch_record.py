from datetime import UTC

from kafka_consumer_py import Effect, EventMessage
from kafka_messages import AccountPostingsDispatched

from data_read_core.shared.postgres_orm import AccountDispatchReadModel

from .._logger_shortcuts import log_dispatch_postgres_recorded
from .._utilities import decode_payload, handle_database_errors


class RecordAccountDispatch(Effect):
    async def apply(self, event: EventMessage) -> None:
        payload = decode_payload(event, AccountPostingsDispatched)
        await handle_database_errors(
            self._record_dispatch,
            payload,
            resource_id=payload.transaction_id,
        )

    async def _record_dispatch(self, payload: AccountPostingsDispatched) -> None:
        dispatched_at = payload.dispatched_at.ToDatetime(tzinfo=UTC)

        await AccountDispatchReadModel.objects.aupdate_or_create(
            transaction_id=payload.transaction_id,
            defaults={
                "user_id": payload.user_id,
                "dispatch_id": payload.dispatch_id,
                "balanced": payload.balanced,
                "comment": payload.comment,
                "backend": payload.backend,
                "created_count": payload.created_count,
                "deleted_count": payload.deleted_count,
                "dispatched_at": dispatched_at,
            },
        )

        log_dispatch_postgres_recorded(payload.transaction_id, payload.balanced)
