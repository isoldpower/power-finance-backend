from kafka_consumer_py import Effect, EventMessage
from kafka_messages import WalletUpdated

from data_read_core.shared.postgres_orm import TransactionReadModel

from .._logger_shortcuts import log_wallet_name_denormalised
from .._utilities import decode_payload, handle_database_errors


class RenameWalletInTransactions(Effect):
    """Carry a wallet rename into the transaction projection, which denormalises
    `wallet.name` onto every row to avoid a join."""

    async def apply(self, event: EventMessage) -> None:
        payload = decode_payload(event, WalletUpdated)
        if payload.new_title == payload.previous_title:
            return

        await handle_database_errors(
            self._rename,
            payload,
            resource_id=payload.wallet_id,
        )

    async def _rename(self, payload: WalletUpdated) -> None:
        updated_row = await TransactionReadModel.objects.filter(
            wallet_id=payload.wallet_id
        ).aupdate(wallet_name=payload.new_title)
        log_wallet_name_denormalised(
            payload.wallet_id,
            updated_row,
        )
