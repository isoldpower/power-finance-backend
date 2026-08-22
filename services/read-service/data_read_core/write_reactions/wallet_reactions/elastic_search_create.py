from datetime import UTC

from kafka_messages import WalletCreated

from data_read_core.shared.elasticsearch import WALLETS_INDEX, get_elasticsearch
from data_read_core.shared.kafka_updates import Effect, EventMessage

from .._logger_shortcuts import log_wallet_elastic_created
from .._utilities import decode_payload


class IndexWalletDocument(Effect):
    """Index the full wallet document into the search index on creation."""

    async def apply(self, event: EventMessage) -> None:
        payload = decode_payload(event, WalletCreated)
        document = {
            "id": payload.wallet_id,
            "user_id": payload.user_id,
            "title": payload.title,
            "currency_code": payload.currency_code,
            "balance": 0,
            "zero_balance": payload.zero_balance or "0",
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
        )
        log_wallet_elastic_created(
            payload.wallet_id,
            WALLETS_INDEX,
        )
