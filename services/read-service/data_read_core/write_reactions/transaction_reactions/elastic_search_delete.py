from kafka_messages import TransactionDeleted

from data_read_core.shared.elasticsearch import TRANSACTIONS_INDEX, get_elasticsearch
from data_read_core.shared.kafka_updates import Effect, EventMessage

from .._logger_shortcuts import log_transaction_elastic_removed
from .._utilities import decode_payload


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

        log_transaction_elastic_removed(payload.transaction_id, TRANSACTIONS_INDEX)
