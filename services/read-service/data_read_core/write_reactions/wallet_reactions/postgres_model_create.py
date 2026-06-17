from datetime import UTC

from kafka_messages import WalletCreated

from data_read_core.shared.kafka_updates import Effect, EventMessage
from data_read_core.shared.postgres_orm import WalletReadModel

from .._logger_shortcuts import log_wallet_postgres_created
from .._utilities import decode_payload, handle_database_errors


class CreateWalletReadModel(Effect):
    async def apply(self, event: EventMessage) -> None:
        payload = decode_payload(event, WalletCreated)
        await handle_database_errors(
            self._create_wallet,
            payload,
            resource_id=payload.wallet_id,
        )

    async def _create_wallet(self, payload: WalletCreated) -> WalletReadModel:
        created_wallet = await WalletReadModel.objects.acreate(
            id=payload.wallet_id,
            user_id=payload.user_id,
            title=payload.title,
            currency_code=payload.currency_code,
            balance=0,
            created_at=payload.created_at.ToDatetime(tzinfo=UTC),
            updated_at=None,
        )
        log_wallet_postgres_created(payload.wallet_id)

        return created_wallet
