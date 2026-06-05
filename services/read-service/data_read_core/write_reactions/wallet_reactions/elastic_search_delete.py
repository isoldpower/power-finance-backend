from logging import getLogger

from kafka_messages import WalletDeleted

from data_read_core.shared.elasticsearch import WALLETS_INDEX, get_elasticsearch
from data_read_core.shared.kafka_updates import Effect, EventMessage

from .._utilities import decode_payload

logger = getLogger("background_workers.write_message_consumer")


class RemoveWalletDocument(Effect):
    """Delete the wallet document from the search index."""

    async def apply(self, event: EventMessage) -> None:
        payload = decode_payload(event, WalletDeleted)
        await (
            get_elasticsearch()
            .options(ignore_status=404)
            .delete(
                index=WALLETS_INDEX,
                id=payload.wallet_id,
            )
        )
        logger.info("Removed wallet %s from %s.", payload.wallet_id, WALLETS_INDEX)
