from datetime import UTC
from decimal import Decimal

from kafka_messages import TransactionCreated

from data_read_core.shared.elasticsearch import TRANSACTIONS_INDEX, get_elasticsearch
from data_read_core.shared.kafka_updates import Effect, EventMessage

from .._logger_shortcuts import log_transaction_elastic_created
from .._utilities import decode_payload
from ._utilities import _wallet_currency


class IndexTransactionDocument(Effect):
    """Index the full transaction document for analytics aggregations."""

    async def apply(self, event: EventMessage) -> None:
        payload = decode_payload(event, TransactionCreated)
        created_at = payload.created_at.ToDatetime(tzinfo=UTC).isoformat()
        document = {
            "id": payload.transaction_id,
            "wallet_id": payload.wallet_id,
            "user_id": payload.user_id,
            "amount": float(Decimal(payload.amount)),
            "currency_code": await _wallet_currency(payload.wallet_id),
            "occurred_at": created_at,
            "created_at": created_at,
        }

        await get_elasticsearch().index(
            index=TRANSACTIONS_INDEX,
            id=payload.transaction_id,
            document=document,
        )
        log_transaction_elastic_created(payload.transaction_id, TRANSACTIONS_INDEX)
