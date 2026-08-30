from datetime import UTC

from kafka_consumer_py import EventMessage
from kafka_consumer_py.processing import Effect
from kafka_messages import WalletDeleted

from data_read_core.shared.postgres_orm import WalletReadModel

from .._logger_shortcuts import log_wallet_postgres_removed
from .._utilities import decode_payload, handle_database_errors


class RemoveWalletReadModel(Effect):
    """Close the wallet projection rather than dropping the row: it leaves lists
    and search but stays queryable by id."""

    async def apply(self, event: EventMessage) -> None:
        event_payload = decode_payload(event, WalletDeleted)
        await handle_database_errors(
            self._close_wallet,
            event_payload,
            resource_id=event_payload.wallet_id,
        )

    async def _close_wallet(self, payload: WalletDeleted) -> None:
        deleted_at = payload.deleted_at.ToDatetime(tzinfo=UTC)
        closed_wallet = await WalletReadModel.objects.filter(id=payload.wallet_id).aupdate(
            deleted_at=deleted_at, updated_at=deleted_at
        )

        log_wallet_postgres_removed(
            payload.wallet_id,
            closed_wallet,
        )
