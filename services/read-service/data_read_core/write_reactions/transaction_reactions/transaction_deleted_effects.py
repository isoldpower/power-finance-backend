from logging import getLogger

from django.db.models import F
from google.protobuf.message import Message
from kafka_messages import TransactionDeleted

from data_read_core.shared.kafka_updates import Effect, EventMessage
from data_read_core.shared.postgres_orm import (
    TransactionReadModel,
    WalletReadModel,
    aatomic,
)
from data_read_core.shared.redis_cache import get_redis

from .._cache_keys import get_single_transaction_key
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
            transaction_row = await (
                TransactionReadModel.objects.select_for_update()
                .filter(id=payload.transaction_id)
                .afirst()
            )

            if transaction_row is None:
                logger.info(
                    "Transaction %s not present; skipping balance reversal.",
                    payload.transaction_id,
                )
                return

            cancelled_amount = transaction_row.amount
            await transaction_row.adelete()
            await WalletReadModel.objects.filter(id=payload.wallet_id).aupdate(
                balance=F("balance") - cancelled_amount
            )

            logger.info(
                "Removed transaction %s and reversed wallet %s balance by %s.",
                payload.transaction_id,
                payload.wallet_id,
                cancelled_amount,
            )


class EvictTransactionCache(Effect):
    def __init__(self, payload_type: type[Message] = TransactionDeleted) -> None:
        self._payload_type = payload_type

    async def apply(self, event: EventMessage) -> None:
        event_payload = decode_payload(event, self._payload_type)
        key = get_single_transaction_key(event_payload.transaction_id)
        removed_resource = await get_redis().delete(key)

        logger.info(
            "Evicted cache key %s (removed=%s).",
            key,
            removed_resource,
        )
