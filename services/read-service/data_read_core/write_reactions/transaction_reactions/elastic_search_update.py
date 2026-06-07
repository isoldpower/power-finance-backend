from decimal import Decimal

from kafka_messages import TransactionUpdated

from data_read_core.shared.elasticsearch import TRANSACTIONS_INDEX, get_elasticsearch
from data_read_core.shared.kafka_updates import Effect, EventMessage

from .._logger_shortcuts import log_transaction_elastic_updated
from .._utilities import decode_payload


class UpdateTransactionDocument(Effect):
    """Patch the amount of a transaction document on update."""

    async def apply(self, event: EventMessage) -> None:
        payload = decode_payload(event, TransactionUpdated)
        partial = {
            "id": payload.transaction_id,
            "wallet_id": payload.wallet_id,
            "user_id": payload.user_id,
            "amount": float(Decimal(payload.new_amount)),
        }

        await get_elasticsearch().update(
            index=TRANSACTIONS_INDEX,
            id=payload.transaction_id,
            doc=partial,
            doc_as_upsert=True,
        )

        log_transaction_elastic_updated(payload.transaction_id, TRANSACTIONS_INDEX)
