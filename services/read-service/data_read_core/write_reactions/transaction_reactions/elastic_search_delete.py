from logging import getLogger

from kafka_messages import TransactionDeleted

from data_read_core.shared.elasticsearch import TRANSACTIONS_INDEX, get_elasticsearch
from data_read_core.shared.kafka_updates import Effect, EventMessage

from .._utilities import decode_payload

logger = getLogger("background_workers.write_message_consumer")


class RemoveTransactionDocument(Effect):
    """Delete the transaction document from the analytics index."""

    async def apply(self, event: EventMessage) -> None:
        payload = decode_payload(event, TransactionDeleted)
        await (
            get_elasticsearch()
            .options(ignore_status=404)
            .delete(
                index=TRANSACTIONS_INDEX,
                id=payload.transaction_id,
            )
        )

        logger.info(
            "Removed transaction %s from %s.",
            payload.transaction_id,
            TRANSACTIONS_INDEX,
        )
