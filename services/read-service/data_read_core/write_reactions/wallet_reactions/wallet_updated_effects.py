from datetime import UTC
from logging import getLogger

from kafka_messages import WalletUpdated

from data_read_core.shared.kafka_updates import Effect, EventMessage
from data_read_core.shared.postgres_orm import WalletReadModel

from .._utilities import decode_payload, handle_database_errors

logger = getLogger("background_workers.write_message_consumer")


class UpdateWalletReadModel(Effect):
    async def apply(self, event: EventMessage) -> None:
        event_payload = decode_payload(event, WalletUpdated)
        await handle_database_errors(
            self._update_wallet,
            event_payload,
            resource_id=event_payload.wallet_id,
        )

    async def _update_wallet(self, payload: WalletUpdated) -> None:
        updated = await WalletReadModel.objects.filter(id=payload.wallet_id).aupdate(
            title=payload.new_title,
            updated_at=payload.updated_at.ToDatetime(tzinfo=UTC),
        )
        logger.info(
            "Updated wallet %s in read store (rows=%s).",
            payload.wallet_id,
            updated,
        )
