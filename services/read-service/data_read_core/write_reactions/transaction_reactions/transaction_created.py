from datetime import UTC, datetime
from decimal import Decimal
from logging import getLogger

from asgiref.sync import sync_to_async
from django.db import transaction
from django.db.models import F
from kafka_messages import TransactionCreated

from data_read_core.shared.kafka_updates import Effect, EventMessage
from data_read_core.shared.postgres_orm import TransactionReadModel, WalletReadModel

from .._utilities import decode_payload, handle_database_errors

logger = getLogger("background_workers.write_message_consumer")


class CreateTransactionReadModel(Effect):
    async def apply(self, event: EventMessage) -> None:
        payload = decode_payload(event, TransactionCreated)
        await handle_database_errors(
            _record_transaction,
            payload,
            resource_id=payload.transaction_id,
        )


async def _record_transaction(payload: TransactionCreated) -> None:
    created_at = payload.created_at.ToDatetime(tzinfo=UTC)
    amount = Decimal(payload.amount)
    await sync_to_async(_persist_transaction)(payload, amount, created_at)


def _persist_transaction(
    payload: TransactionCreated,
    amount: Decimal,
    created_at: datetime,
) -> None:
    with transaction.atomic():
        _, created = TransactionReadModel.objects.get_or_create(
            id=payload.transaction_id,
            defaults={
                "wallet_id": payload.wallet_id,
                "user_id": payload.user_id,
                "amount": amount,
                "occurred_at": created_at,
                "created_at": created_at,
            },
        )
        if not created:
            logger.info(
                "Transaction %s already projected; skipping balance adjustment.",
                payload.transaction_id,
            )
            return

        adjusted = WalletReadModel.objects.filter(id=payload.wallet_id).update(
            balance=F("balance") + amount,
        )
        logger.info(
            "Recorded transaction %s and adjusted wallet %s balance by %s (rows=%s).",
            payload.transaction_id,
            payload.wallet_id,
            amount,
            adjusted,
        )
