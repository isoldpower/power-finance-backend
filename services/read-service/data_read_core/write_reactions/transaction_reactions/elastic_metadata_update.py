from datetime import UTC

from kafka_consumer_py import Effect, EventMessage
from kafka_messages import TransactionMetadataUpdated

from data_read_core.shared.elasticsearch import TRANSACTIONS_INDEX, get_elasticsearch

from .._logger_shortcuts import log_transaction_elastic_updated
from .._utilities import decode_payload


class UpdateTransactionMetadataDocument(Effect):
    async def apply(self, event: EventMessage) -> None:
        payload = decode_payload(event, TransactionMetadataUpdated)
        partial = {
            "id": payload.transaction_id,
            "user_id": payload.user_id,
            "name": payload.name,
            "category": payload.category or None,
            "evidence_url": payload.evidence_url or None,
            "updated_at": payload.updated_at.ToDatetime(tzinfo=UTC).isoformat(),
        }

        await get_elasticsearch().update(
            index=TRANSACTIONS_INDEX,
            id=payload.transaction_id,
            doc=partial,
            doc_as_upsert=True,
        )
        log_transaction_elastic_updated(
            payload.transaction_id,
            TRANSACTIONS_INDEX,
        )
