from datetime import UTC
from decimal import Decimal

from kafka_messages import WalletUpdated

from data_read_core.shared.kafka_updates import Effect, EventMessage
from data_read_core.shared.postgres_orm import WalletReadModel

from .._logger_shortcuts import log_wallet_postgres_updated
from .._utilities import decode_payload, handle_database_errors


class UpdateWalletReadModel(Effect):
    async def apply(self, event: EventMessage) -> None:
        event_payload = decode_payload(event, WalletUpdated)
        await handle_database_errors(
            self._update_wallet,
            event_payload,
            resource_id=event_payload.wallet_id,
        )

    async def _update_wallet(self, payload: WalletUpdated) -> None:
        updated_row = await WalletReadModel.objects.filter(id=payload.wallet_id).aupdate(
            title=payload.new_title,
            updated_at=payload.updated_at.ToDatetime(tzinfo=UTC),
            category=payload.category,
            color=payload.color,
            favorite=payload.favorite,
            zero_balance=Decimal(payload.zero_balance or "0"),
        )

        log_wallet_postgres_updated(
            payload.wallet_id,
            updated_row,
        )
