from decimal import Decimal

from kafka_consumer_py import Effect, EventMessage
from kafka_messages import TransactionUpdated

from data_read_core.shared.postgres_orm import (
    NO_CHAIN_SENTINEL,
    TransactionReadModel,
    aatomic,
)

from .._logger_shortcuts import (
    log_transaction_postgres_absent_on_update,
    log_transaction_postgres_chain_changed,
    log_transaction_postgres_unchanged,
    log_transaction_postgres_updated,
)
from .._utilities import decode_payload, handle_database_errors
from ._utilities import apply_container_delta


class UpdateTransactionReadModel(Effect):
    async def apply(self, event: EventMessage) -> None:
        payload = decode_payload(event, TransactionUpdated)
        await handle_database_errors(
            self._update_transaction,
            payload,
            resource_id=payload.transaction_id,
        )

    async def _update_transaction(
        self,
        payload: TransactionUpdated,
    ) -> None:
        async with aatomic():
            await self._apply_all_updates(
                new_amount=Decimal(payload.new_amount),
                transaction_id=payload.transaction_id,
                chain_id=payload.chain_id or None,
            )

    async def _apply_all_updates(
        self,
        new_amount: Decimal,
        transaction_id: str,
        chain_id: str | None,
    ) -> None:
        new_amount = Decimal(new_amount)
        transaction_row = await (
            TransactionReadModel.objects.select_for_update().filter(id=transaction_id).afirst()
        )

        if transaction_row is not None:
            amount_delta = await self._apply_transaction_update(
                transaction_row,
                new_amount,
            )
            # Chain membership rides along as current state, so it is applied on its
            # own: an event that only releases a transaction from its chain carries
            # an unchanged amount and would otherwise be discarded as a no-op.
            await self._apply_chain_update(transaction_row, chain_id)
            await self._apply_container_update(
                transaction_row.wallet_id,
                transaction_row.container_kind,
                amount_delta,
            )
        else:
            log_transaction_postgres_absent_on_update(transaction_id)

    async def _apply_transaction_update(
        self,
        transaction_row: TransactionReadModel,
        new_amount: Decimal,
    ) -> Decimal | None:
        if transaction_row.amount == new_amount:
            log_transaction_postgres_unchanged(
                transaction_row.id,
                new_amount,
            )
            return None

        amount_delta = new_amount - transaction_row.amount
        transaction_row.amount = new_amount
        await transaction_row.asave(update_fields=["amount"])

        log_transaction_postgres_updated(
            transaction_row.id,
            new_amount,
            transaction_row.wallet_id,
            amount_delta,
        )
        return amount_delta

    async def _apply_chain_update(
        self,
        transaction_row: TransactionReadModel,
        chain_id: str | None,
    ) -> None:
        if str(transaction_row.chain_id or "") == str(chain_id or ""):
            return

        transaction_row.chain_id = chain_id
        transaction_row.chain_sort = chain_id or NO_CHAIN_SENTINEL
        await transaction_row.asave(update_fields=["chain_id", "chain_sort"])

        log_transaction_postgres_chain_changed(transaction_row.id, chain_id)

    async def _apply_container_update(
        self,
        container_id: str,
        kind: str,
        amount_delta: Decimal | None,
    ) -> None:
        if not amount_delta:
            return

        await apply_container_delta(
            container_id,
            kind,
            amount_delta,
        )
