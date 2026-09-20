from datetime import UTC
from decimal import Decimal

from kafka_consumer_py import Effect, EventMessage
from kafka_messages import WalletCreated

from data_read_core.shared.elasticsearch import (
    SEARCHABLE_REFRESH,
    WALLETS_INDEX,
    get_elasticsearch,
)

from .._logger_shortcuts import log_wallet_elastic_created
from .._utilities import decode_payload


class IndexWalletDocument(Effect):
    async def apply(self, event: EventMessage) -> None:
        """Seed the wallet document.

        `balance` and `zero_balance` are floats, not ints or strings: the
        balance is adjusted in place by a Painless script, and `+=` casts its
        result back to the left operand's type. An integer seed silently
        truncates every fractional delta.
        """

        payload = decode_payload(event, WalletCreated)
        document = {
            "id": payload.wallet_id,
            "user_id": payload.user_id,
            "title": payload.title,
            "currency_code": payload.currency_code,
            "balance": 0.0,
            "zero_balance": float(Decimal(payload.zero_balance or "0")),
            "created_at": payload.created_at.ToDatetime(tzinfo=UTC).isoformat(),
            "updated_at": None,
            "deleted_at": None,
            "category": payload.category,
            "color": payload.color,
            "favorite": payload.favorite,
        }

        await get_elasticsearch().index(
            index=WALLETS_INDEX,
            id=payload.wallet_id,
            document=document,
            refresh=SEARCHABLE_REFRESH,
        )
        log_wallet_elastic_created(
            payload.wallet_id,
            WALLETS_INDEX,
        )
