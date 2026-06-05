from decimal import Decimal
from logging import getLogger

from django.db.models import F
from kafka_messages import TransactionDeleted

from data_read_core.shared.kafka_updates import Effect, EventMessage
from data_read_core.shared.postgres_orm import (
    TransactionReadModel,
    WalletReadModel,
    aatomic,
)

from .._utilities import decode_payload, handle_database_errors

logger = getLogger("background_workers.write_message_consumer")


class RemoveTransactionReadModel(Effect):
    async def apply(self, event: EventMessage) -> None:
        payload = decode_payload(event, TransactionDeleted)
        await handle_database_errors(
            self._remove_transaction,
            payload,
            resource_id=payload.transaction_id,
        )

    async def _remove_transaction(
        self,
        payload: TransactionDeleted,
    ) -> None:
        async with aatomic():
            cancelled_transaction = await self._try_delete_transaction(payload.transaction_id)

            if cancelled_transaction:
                await self._apply_wallet_update(
                    wallet_id=cancelled_transaction.wallet_id,
                    cancelled_amount=cancelled_transaction.amount,
                )

    async def _try_delete_transaction(
        self,
        transaction_id: str,
    ) -> TransactionReadModel | None:
        transaction_row = await (
            TransactionReadModel.objects.select_for_update().filter(id=transaction_id).afirst()
        )

        if transaction_row is None:
            logger.info(
                "Transaction %s not present; skipping balance reversal.",
                transaction_id,
            )

            return None

        await transaction_row.adelete()
        logger.info(
            "Removed transaction %s with value of %d.",
            transaction_id,
            transaction_row.amount,
        )

        return transaction_row

    async def _apply_wallet_update(
        self,
        wallet_id: str,
        cancelled_amount: Decimal,
    ):
        (
            await WalletReadModel.objects.filter(id=wallet_id).aupdate(
                balance=F("balance") - cancelled_amount
            )
        )

        logger.info(
            "Reversed wallet %s balance by %s.",
            wallet_id,
            cancelled_amount,
        )
