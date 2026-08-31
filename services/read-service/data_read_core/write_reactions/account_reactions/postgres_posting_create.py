from datetime import UTC

from kafka_consumer_py import Effect, EventMessage
from kafka_messages import AccountPostingCreated

from data_read_core.shared.postgres_orm import AccountPostingReadModel

from .._logger_shortcuts import (
    log_posting_postgres_created,
    log_posting_postgres_duplication,
)
from .._utilities import decode_payload, handle_database_errors
from ._utilities import money_of


class CreateAccountPostingReadModel(Effect):
    async def apply(self, event: EventMessage) -> None:
        payload = decode_payload(event, AccountPostingCreated)
        await handle_database_errors(
            self._record_posting,
            payload,
            resource_id=payload.posting_id,
        )

    async def _record_posting(self, payload: AccountPostingCreated) -> None:
        created_at = payload.created_at.ToDatetime(tzinfo=UTC)

        _, posting_created = await AccountPostingReadModel.objects.aget_or_create(
            id=payload.posting_id,
            defaults={
                "user_id": payload.user_id,
                "account_id": payload.account_id,
                "transaction_id": payload.transaction_id,
                "dispatch_id": payload.dispatch_id or None,
                "title": payload.title,
                "icon": payload.icon,
                "debit": payload.debit,
                "amount": money_of(payload.amount),
                "currency_code": payload.currency_code,
                "position": payload.position,
                "created_at": created_at,
            },
        )

        if posting_created:
            log_posting_postgres_created(payload.posting_id, payload.transaction_id)
        else:
            log_posting_postgres_duplication(payload.posting_id)
