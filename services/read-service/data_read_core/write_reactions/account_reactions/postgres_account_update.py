from datetime import UTC

from kafka_consumer_py import Effect, EventMessage
from kafka_messages import AccountUpdated

from data_read_core.shared.postgres_orm import AccountReadModel

from .._logger_shortcuts import log_account_postgres_updated
from .._utilities import decode_payload, handle_database_errors
from ._utilities import group_name_of, money_of


class UpdateAccountReadModel(Effect):
    async def apply(self, event: EventMessage) -> None:
        payload = decode_payload(event, AccountUpdated)
        await handle_database_errors(
            self._restate_account,
            payload,
            resource_id=payload.account_id,
        )

    async def _restate_account(self, payload: AccountUpdated) -> None:
        updated_at = payload.updated_at.ToDatetime(tzinfo=UTC)
        new_balance = money_of(payload.new_balance)

        await AccountReadModel.objects.aupdate_or_create(
            id=payload.account_id,
            defaults={
                "user_id": payload.user_id,
                "group": group_name_of(payload.account_group),
                "name": payload.name,
                "balance": new_balance,
                "updated_at": updated_at,
            },
            create_defaults={
                "user_id": payload.user_id,
                "group": group_name_of(payload.account_group),
                "name": payload.name,
                "balance": new_balance,
                "created_at": updated_at,
                "updated_at": updated_at,
            },
        )

        log_account_postgres_updated(payload.account_id, new_balance)
