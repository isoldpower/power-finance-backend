from datetime import UTC
from decimal import Decimal

from kafka_consumer_py import Effect, EventMessage
from kafka_messages import TransactionCreated

from data_read_core.shared.elasticsearch import TRANSACTIONS_INDEX, get_elasticsearch
from data_read_core.shared.postgres_orm import NO_CHAIN_SENTINEL

from .._logger_shortcuts import log_transaction_elastic_created
from .._utilities import decode_payload
from ._utilities import _container_label


class IndexTransactionDocument(Effect):
    """Index the full transaction document into the search index on creation."""

    async def apply(self, event: EventMessage) -> None:
        payload = decode_payload(event, TransactionCreated)
        wallet = await _container_label(
            payload.wallet_id,
            payload.container_kind or None,
        )
        amount = Decimal(payload.amount)
        created_at = payload.created_at.ToDatetime(tzinfo=UTC).isoformat()

        document = {
            "id": payload.transaction_id,
            "wallet_id": payload.wallet_id,
            "wallet_name": wallet.name,
            "user_id": payload.user_id,
            "amount": float(amount),
            "currency_code": wallet.currency_code,
            "name": payload.name,
            "category": payload.category or None,
            "evidence_url": payload.evidence_url or None,
            "origin": payload.origin or "manual",
            "type": "expense" if amount < 0 else "income",
            "chain_id": payload.chain_id or None,
            "chain_sort": payload.chain_id or str(NO_CHAIN_SENTINEL),
            "occurred_at": created_at,
            "created_at": created_at,
            "updated_at": None,
            "deleted_at": None,
        }

        await get_elasticsearch().index(
            index=TRANSACTIONS_INDEX,
            id=payload.transaction_id,
            document=document,
        )
        log_transaction_elastic_created(
            payload.transaction_id,
            TRANSACTIONS_INDEX,
        )
