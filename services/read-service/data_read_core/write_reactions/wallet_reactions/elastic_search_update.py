from datetime import UTC

from kafka_messages import WalletUpdated

from data_read_core.shared.elasticsearch import WALLETS_INDEX, get_elasticsearch
from data_read_core.shared.kafka_updates import Effect, EventMessage

from .._logger_shortcuts import log_wallet_elastic_updated
from .._utilities import decode_payload


class UpdateWalletDocument(Effect):
    """Patch the searchable fields of a wallet document on update. Upserts so an
    edit that races ahead of the create projection still lands."""

    async def apply(self, event: EventMessage) -> None:
        payload = decode_payload(event, WalletUpdated)
        partial = {
            "id": payload.wallet_id,
            "user_id": payload.user_id,
            "title": payload.new_title,
            "updated_at": payload.updated_at.ToDatetime(tzinfo=UTC).isoformat(),
            "category": payload.category,
            "color": payload.color,
            "favorite": payload.favorite,
            "zero_balance": payload.zero_balance or "0",
        }

        await get_elasticsearch().update(
            index=WALLETS_INDEX,
            id=payload.wallet_id,
            doc=partial,
            doc_as_upsert=True,
        )
        log_wallet_elastic_updated(
            payload.wallet_id,
            WALLETS_INDEX,
        )
