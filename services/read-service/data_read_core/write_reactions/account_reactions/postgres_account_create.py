from datetime import UTC

from kafka_consumer_py import Effect, EventMessage
from kafka_messages import AccountCreated

from data_read_core.shared.postgres_orm import AccountReadModel

from .._logger_shortcuts import (
    log_account_postgres_created,
    log_account_postgres_duplication,
)
from .._utilities import (
    decode_payload,
    handle_database_errors,
)
from ._utilities import (
    book_currency_of,
    group_name_of,
    money_of,
)


class CreateAccountReadModel(Effect):
    async def apply(self, event: EventMessage) -> None:
        payload = decode_payload(event, AccountCreated)
        await handle_database_errors(
            self._record_account,
            payload,
            resource_id=payload.account_id,
        )

    async def _record_account(self, payload: AccountCreated) -> None:
        created_at = payload.created_at.ToDatetime(tzinfo=UTC)

        _, account_created = await AccountReadModel.objects.aget_or_create(
            id=payload.account_id,
            defaults={
                "user_id": payload.user_id,
                "group": group_name_of(payload.account_group),
                "name": payload.name,
                "balance": money_of(payload.balance),
                "currency_code": book_currency_of(payload.currency_code),
                "created_at": created_at,
            },
        )

        if account_created:
            log_account_postgres_created(
                payload.account_id,
                payload.name,
            )
        else:
            log_account_postgres_duplication(payload.account_id)
