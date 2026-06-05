from decimal import Decimal
from logging import getLogger

from django.db.models import F
from kafka_messages import TransactionUpdated

from data_read_core.shared.kafka_updates import Effect, EventMessage
from data_read_core.shared.postgres_orm import (
    TransactionReadModel,
    WalletReadModel,
    aatomic,
)

from .._utilities import decode_payload, handle_database_errors

logger = getLogger("background_workers.write_message_consumer")


class UpdateTransactionReadModel(Effect):
    async def apply(self, event: EventMessage) -> None:
        payload = decode_payload(event, TransactionUpdated)
        await handle_database_errors(
            self._update_transaction,
            payload,
            resource_id=payload.transaction_id,
        )

    async def _update_transaction(
        self,
        payload: TransactionUpdated,
    ) -> None:
        async with aatomic():
            await self._apply_all_updates(
                new_amount=Decimal(payload.new_amount),
                transaction_id=payload.transaction_id,
            )

    async def _apply_all_updates(
        self,
        new_amount: Decimal,
        transaction_id: str,
    ) -> None:
        new_amount = Decimal(new_amount)
        transaction_row = await (
            TransactionReadModel.objects.select_for_update().filter(id=transaction_id).afirst()
        )

        if transaction_row is not None:
            transaction_row = await self._apply_transaction_update(
                transaction_row,
                new_amount,
            )
            await self._apply_wallet_update(transaction_row, new_amount)
        else:
            logger.info(
                "Transaction %s not present; skipping update.",
                transaction_id,
            )

    async def _apply_transaction_update(
        self,
        transaction_row: TransactionReadModel | None,
        new_amount: Decimal,
    ) -> TransactionReadModel | None:
        if transaction_row.amount == new_amount:
            logger.info(
                "Transaction %s already at amount %s; skipping.",
                transaction_row.id,
                new_amount,
            )
            return None

        amount_delta = new_amount - transaction_row.amount
        transaction_row.amount = new_amount
        await transaction_row.asave(update_fields=["amount"])

        logger.info(
            "Updated transaction %s amount to %s and adjusted wallet %s balance by %s.",
            transaction_row.id,
            new_amount,
            transaction_row.wallet_id,
            amount_delta,
        )
        return transaction_row

    async def _apply_wallet_update(
        self,
        transaction_row: TransactionReadModel | None,
        new_amount: Decimal,
    ) -> None:
        if not transaction_row:
            return

        amount_delta = new_amount - transaction_row.amount
        await WalletReadModel.objects.filter(id=transaction_row.wallet_id).aupdate(
            balance=F("balance") + amount_delta
        )
