from datetime import UTC

from kafka_consumer_py import Effect, EventMessage
from kafka_messages import WalletDeleted

from data_read_core.shared.elasticsearch import WALLETS_INDEX, get_elasticsearch

from .._logger_shortcuts import log_wallet_elastic_removed
from .._utilities import decode_payload


class RemoveWalletDocument(Effect):
    """Stamp the document closed instead of deleting it; search filters on
    `deleted_at`, so both projections tell the same story."""

    async def apply(self, event: EventMessage) -> None:
        payload = decode_payload(event, WalletDeleted)
        deleted_at = payload.deleted_at.ToDatetime(tzinfo=UTC).isoformat()

        await (
            get_elasticsearch()
            .options(ignore_status=404)
            .update(
                index=WALLETS_INDEX,
                id=payload.wallet_id,
                doc={"deleted_at": deleted_at, "updated_at": deleted_at},
            )
        )
        log_wallet_elastic_removed(
            payload.wallet_id,
            WALLETS_INDEX,
        )
