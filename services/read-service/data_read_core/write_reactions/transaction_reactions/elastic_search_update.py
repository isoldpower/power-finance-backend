from decimal import Decimal

from kafka_consumer_py import Effect, EventMessage
from kafka_messages import TransactionUpdated

from data_read_core.shared.elasticsearch import (
    SEARCHABLE_REFRESH,
    TRANSACTIONS_INDEX,
    get_elasticsearch,
)
from data_read_core.shared.postgres_orm import NO_CHAIN_SENTINEL

from .._logger_shortcuts import log_transaction_elastic_updated
from .._utilities import decode_payload


class UpdateTransactionDocument(Effect):
    async def apply(self, event: EventMessage) -> None:
        payload = decode_payload(event, TransactionUpdated)
        chain_id = payload.chain_id or None
        partial = {
            "id": payload.transaction_id,
            "wallet_id": payload.wallet_id,
            "user_id": payload.user_id,
            "amount": float(Decimal(payload.new_amount)),
            "chain_id": chain_id,
            "chain_sort": chain_id or str(NO_CHAIN_SENTINEL),
        }

        await get_elasticsearch().update(
            index=TRANSACTIONS_INDEX,
            id=payload.transaction_id,
            doc=partial,
            doc_as_upsert=True,
            refresh=SEARCHABLE_REFRESH,
        )

        log_transaction_elastic_updated(
            payload.transaction_id,
            TRANSACTIONS_INDEX,
        )
