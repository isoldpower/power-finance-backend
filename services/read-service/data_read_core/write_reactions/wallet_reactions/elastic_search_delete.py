from kafka_messages import WalletDeleted

from data_read_core.shared.elasticsearch import WALLETS_INDEX, get_elasticsearch
from data_read_core.shared.kafka_updates import Effect, EventMessage

from .._logger_shortcuts import log_wallet_elastic_removed
from .._utilities import decode_payload


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
        log_wallet_elastic_removed(payload.wallet_id, WALLETS_INDEX)
