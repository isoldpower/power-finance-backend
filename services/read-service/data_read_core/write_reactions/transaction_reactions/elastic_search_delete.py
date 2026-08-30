from datetime import UTC

from kafka_consumer_py import Effect, EventMessage
from kafka_messages import TransactionDeleted

from data_read_core.shared.elasticsearch import TRANSACTIONS_INDEX, get_elasticsearch

from .._logger_shortcuts import log_transaction_elastic_removed
from .._utilities import decode_payload


class RemoveTransactionDocument(Effect):
    """Stamp the document cancelled instead of deleting it; search filters on
    `deleted_at`, so both projections tell the same story."""

    async def apply(self, event: EventMessage) -> None:
        payload = decode_payload(event, TransactionDeleted)
        deleted_at = payload.deleted_at.ToDatetime(tzinfo=UTC).isoformat()

        await (
            get_elasticsearch()
            .options(ignore_status=404)
            .update(
                index=TRANSACTIONS_INDEX,
                id=payload.transaction_id,
                doc={
                    "deleted_at": deleted_at,
                    "updated_at": deleted_at,
                },
            )
        )
        log_transaction_elastic_removed(
            payload.transaction_id,
            TRANSACTIONS_INDEX,
        )
