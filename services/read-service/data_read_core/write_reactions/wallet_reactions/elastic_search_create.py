from datetime import UTC
from logging import getLogger

from kafka_messages import WalletCreated

from data_read_core.shared.elasticsearch import WALLETS_INDEX, get_elasticsearch
from data_read_core.shared.kafka_updates import Effect, EventMessage

from .._utilities import decode_payload

logger = getLogger("background_workers.write_message_consumer")


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
            "created_at": payload.created_at.ToDatetime(tzinfo=UTC).isoformat(),
            "updated_at": None,
        }

        await get_elasticsearch().index(
            index=WALLETS_INDEX,
            id=payload.wallet_id,
            document=document,
        )
        logger.info(
            "Indexed wallet %s into %s.",
            payload.wallet_id,
            WALLETS_INDEX,
        )
