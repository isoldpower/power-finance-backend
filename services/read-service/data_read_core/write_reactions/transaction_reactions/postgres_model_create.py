from datetime import UTC, datetime
from decimal import Decimal
from logging import getLogger

from django.db.models import F
from kafka_messages import TransactionCreated

from data_read_core.shared.kafka_updates import Effect, EventMessage
from data_read_core.shared.postgres_orm import TransactionReadModel, WalletReadModel, aatomic

from .._utilities import decode_payload, handle_database_errors
from ._utilities import _wallet_currency

logger = getLogger("background_workers.write_message_consumer")


class CreateTransactionReadModel(Effect):
    async def apply(self, event: EventMessage) -> None:
        payload = decode_payload(event, TransactionCreated)
        await handle_database_errors(
            self._record_transaction,
            payload,
            resource_id=payload.transaction_id,
        )

    async def _record_transaction(
        self,
        payload: TransactionCreated,
    ) -> None:
        created_at = payload.created_at.ToDatetime(tzinfo=UTC)
        amount = Decimal(payload.amount)

        await self._persist_transaction(
            payload=payload,
            amount=amount,
            created_at=created_at,
        )

    async def _persist_transaction(
        self,
        payload: TransactionCreated,
        amount: Decimal,
        created_at: datetime,
    ) -> None:
        async with aatomic():
            created_transaction = await self._try_create_transaction(
                amount=amount,
                payload=payload,
                created_at=created_at,
            )
            await self._apply_wallet_update(created_transaction)

    async def _try_create_transaction(
        self,
        amount: Decimal,
        payload: TransactionCreated,
        created_at: datetime,
    ) -> TransactionReadModel | None:
        currency_code = await _wallet_currency(payload.wallet_id)
        new_resource, resource_created = await TransactionReadModel.objects.aget_or_create(
            id=payload.transaction_id,
            defaults={
                "wallet_id": payload.wallet_id,
                "user_id": payload.user_id,
                "amount": amount,
                "currency_code": currency_code,
                "occurred_at": created_at,
                "created_at": created_at,
            },
        )

        if not resource_created:
            logger.info(
                "Transaction %s already projected; skipping balance adjustment.",
                payload.transaction_id,
            )
        else:
            logger.info(
                "Recorded transaction %s with value %d.",
                new_resource.id,
                new_resource.amount,
            )

        return new_resource

    async def _apply_wallet_update(
        self,
        transaction_row: TransactionReadModel | None,
    ) -> None:
        if not transaction_row:
            return

        adjusted_count = await WalletReadModel.objects.filter(id=transaction_row.wallet_id).aupdate(
            balance=F("balance") + transaction_row.amount
        )
        logger.info(
            "Adjusted wallet %s balance by %s (rows=%s).",
            transaction_row.wallet_id,
            transaction_row.amount,
            adjusted_count,
        )
