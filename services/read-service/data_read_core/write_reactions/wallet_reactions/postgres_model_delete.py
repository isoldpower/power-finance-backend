from kafka_messages import WalletDeleted

from data_read_core.shared.kafka_updates import EventMessage
from data_read_core.shared.kafka_updates.processing import Effect
from data_read_core.shared.postgres_orm import WalletReadModel

from .._logger_shortcuts import log_wallet_postgres_removed
from .._utilities import decode_payload, handle_database_errors


class RemoveWalletReadModel(Effect):
    """Delete the wallet projection row from the read store."""

    async def apply(self, event: EventMessage) -> None:
        event_payload = decode_payload(event, WalletDeleted)
        await handle_database_errors(
            self._remove_wallet,
            event_payload,
            resource_id=event_payload.wallet_id,
        )

    async def _remove_wallet(self, payload: WalletDeleted) -> None:
        deleted, _ = await WalletReadModel.objects.filter(id=payload.wallet_id).adelete()
        log_wallet_postgres_removed(payload.wallet_id, deleted)
