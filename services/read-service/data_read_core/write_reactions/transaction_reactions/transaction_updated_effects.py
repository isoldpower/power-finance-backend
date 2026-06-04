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
        new_amount = Decimal(payload.new_amount)
        await self._apply_update(payload, new_amount)

    async def _apply_update(
        self,
        payload: TransactionUpdated,
        new_amount: Decimal,
    ) -> None:
        async with aatomic():
            row = await (
                TransactionReadModel.objects.select_for_update()
                .filter(id=payload.transaction_id)
                .afirst()
            )

            if row is None:
                logger.info(
                    "Transaction %s not present; skipping update.",
                    payload.transaction_id,
                )
                return
            if row.amount == new_amount:
                logger.info(
                    "Transaction %s already at amount %s; skipping.",
                    payload.transaction_id,
                    new_amount,
                )
                return

            amount_delta = new_amount - row.amount
            row.amount = new_amount
            await row.asave(update_fields=["amount"])
            await WalletReadModel.objects.filter(id=payload.wallet_id).aupdate(
                balance=F("balance") + amount_delta
            )

            logger.info(
                "Updated transaction %s amount to %s and adjusted wallet %s balance by %s.",
                payload.transaction_id,
                new_amount,
                payload.wallet_id,
                amount_delta,
            )
