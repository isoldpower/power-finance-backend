from datetime import UTC
from decimal import Decimal

from django.db.models import F
from kafka_messages import TransactionDeleted

from data_read_core.shared.kafka_updates import Effect, EventMessage
from data_read_core.shared.postgres_orm import (
    TransactionReadModel,
    WalletReadModel,
    aatomic,
)

from .._logger_shortcuts import (
    log_transaction_postgres_absent_on_delete,
    log_transaction_postgres_removed,
    log_transaction_postgres_wallet_reversal,
)
from .._utilities import decode_payload, handle_database_errors


class RemoveTransactionReadModel(Effect):
    async def apply(self, event: EventMessage) -> None:
        payload = decode_payload(event, TransactionDeleted)
        await handle_database_errors(
            self._cancel_transaction,
            payload,
            resource_id=payload.transaction_id,
        )

    async def _cancel_transaction(self, payload: TransactionDeleted) -> None:
        async with aatomic():
            cancelled_transaction = await self._try_cancel(payload)

            if cancelled_transaction:
                await self._apply_wallet_update(
                    wallet_id=cancelled_transaction.wallet_id,
                    cancelled_amount=cancelled_transaction.amount,
                )

    async def _try_cancel(self, payload: TransactionDeleted) -> TransactionReadModel | None:
        transaction_row = await (
            TransactionReadModel.objects.select_for_update()
            .filter(id=payload.transaction_id)
            .afirst()
        )

        if transaction_row is None:
            log_transaction_postgres_absent_on_delete(payload.transaction_id)
            return None
        elif transaction_row.deleted_at is not None:
            return None

        deleted_at = payload.deleted_at.ToDatetime(tzinfo=UTC)
        transaction_row.deleted_at = deleted_at
        transaction_row.updated_at = deleted_at
        await transaction_row.asave(update_fields=["deleted_at", "updated_at"])

        log_transaction_postgres_removed(payload.transaction_id, transaction_row.amount)
        return transaction_row

    async def _apply_wallet_update(
        self,
        wallet_id: str,
        cancelled_amount: Decimal,
    ) -> None:
        (
            await WalletReadModel.objects.filter(id=wallet_id).aupdate(
                balance=F("balance") - cancelled_amount
            )
        )

        log_transaction_postgres_wallet_reversal(
            wallet_id,
            cancelled_amount,
        )
