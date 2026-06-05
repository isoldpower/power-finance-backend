from datetime import UTC
from logging import getLogger

from kafka_messages import WalletUpdated

from data_read_core.shared.elasticsearch import WALLETS_INDEX, get_elasticsearch
from data_read_core.shared.kafka_updates import Effect, EventMessage

from .._utilities import decode_payload

logger = getLogger("background_workers.write_message_consumer")


class UpdateWalletDocument(Effect):
    """Patch the searchable fields of a wallet document on update. Upserts so a
    title edit that races ahead of the create projection still lands."""

    async def apply(self, event: EventMessage) -> None:
        payload = decode_payload(event, WalletUpdated)
        partial = {
            "id": payload.wallet_id,
            "user_id": payload.user_id,
            "title": payload.new_title,
            "updated_at": payload.updated_at.ToDatetime(tzinfo=UTC).isoformat(),
        }

        await get_elasticsearch().update(
            index=WALLETS_INDEX,
            id=payload.wallet_id,
            doc=partial,
            doc_as_upsert=True,
        )
        logger.info(
            "Updated wallet %s in %s.",
            payload.wallet_id,
            WALLETS_INDEX,
        )
