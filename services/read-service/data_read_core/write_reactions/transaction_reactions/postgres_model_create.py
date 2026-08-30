from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from kafka_consumer_py import (
    Effect,
    EventMessage,
)
from kafka_messages import TransactionCreated

from data_read_core.shared.postgres_orm import (
    NO_CHAIN_SENTINEL,
    TransactionReadModel,
    aatomic,
)

from .._logger_shortcuts import (
    log_transaction_postgres_container_update,
    log_transaction_postgres_created,
    log_transaction_postgres_duplication,
)
from .._utilities import decode_payload, handle_database_errors
from ._utilities import _container_label, apply_container_delta


class CreateTransactionReadModel(Effect):
    async def apply(self, event: EventMessage) -> None:
        payload = decode_payload(event, TransactionCreated)
        await handle_database_errors(
            self._record_transaction,
            payload,
            resource_id=payload.transaction_id,
        )

    async def _record_transaction(
        self,
        payload: TransactionCreated,
    ) -> None:
        created_at = payload.created_at.ToDatetime(tzinfo=UTC)
        amount = Decimal(payload.amount)

        await self._persist_transaction(
            payload=payload,
            amount=amount,
            created_at=created_at,
        )

    async def _persist_transaction(
        self,
        payload: TransactionCreated,
        amount: Decimal,
        created_at: datetime,
    ) -> None:
        async with aatomic():
            created_transaction = await self._try_create_transaction(
                amount=amount,
                payload=payload,
                created_at=created_at,
            )
            await self._apply_wallet_update(created_transaction)

    async def _try_create_transaction(
        self,
        amount: Decimal,
        payload: TransactionCreated,
        created_at: datetime,
    ) -> TransactionReadModel | None:
        container = await _container_label(
            payload.wallet_id,
            payload.container_kind or None,
        )
        chain_id = UUID(payload.chain_id) if payload.chain_id else None

        new_resource, resource_created = await TransactionReadModel.objects.aget_or_create(
            id=payload.transaction_id,
            defaults={
                "wallet_id": payload.wallet_id,
                "wallet_name": container.name,
                "container_kind": container.kind,
                "user_id": payload.user_id,
                "amount": amount,
                "currency_code": container.currency_code,
                "name": payload.name,
                "category": payload.category or None,
                "evidence_url": payload.evidence_url or None,
                "origin": payload.origin or "manual",
                "chain_id": chain_id,
                "chain_sort": chain_id or NO_CHAIN_SENTINEL,
                "occurred_at": created_at,
                "created_at": created_at,
            },
        )

        if not resource_created:
            log_transaction_postgres_duplication(
                payload.transaction_id,
            )
        else:
            log_transaction_postgres_created(
                new_resource.id,
                new_resource.amount,
            )
        return new_resource

    async def _apply_wallet_update(
        self,
        transaction_row: TransactionReadModel | None,
    ) -> None:
        if not transaction_row:
            return

        adjusted_count = await apply_container_delta(
            transaction_row.wallet_id,
            transaction_row.container_kind,
            transaction_row.amount,
        )
        log_transaction_postgres_container_update(
            transaction_row.id,
            transaction_row.amount,
            adjusted_count,
        )
