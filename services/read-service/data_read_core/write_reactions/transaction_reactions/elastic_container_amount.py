from decimal import Decimal
from typing import NamedTuple

from elasticsearch import NotFoundError
from kafka_consumer_py import Effect, EventMessage
from kafka_messages import TransactionCreated, TransactionDeleted, TransactionUpdated

from data_read_core.shared.elasticsearch import (
    GOALS_INDEX,
    SEARCHABLE_REFRESH,
    WALLETS_INDEX,
    get_elasticsearch,
)
from data_read_core.shared.postgres_orm import MoneyContainers, TransactionReadModel

from .._logger_shortcuts import (
    log_container_amount_elastic_absent,
    log_container_amount_elastic_adjusted,
)
from .._utilities import decode_payload

WALLET_BALANCE_ADJUSTMENT_SCRIPT = "ctx._source.balance += params.delta"
GOAL_PROGRESS_ADJUSTMENT_SCRIPT = "ctx._source.progress += params.delta"
CONFLICT_RETRIES = 3


class IndexedContainerTarget(NamedTuple):
    index_name: str
    adjustment_script: str


_INDEXED_CONTAINERS: dict[str, IndexedContainerTarget] = {
    MoneyContainers.WALLET: IndexedContainerTarget(
        WALLETS_INDEX,
        WALLET_BALANCE_ADJUSTMENT_SCRIPT,
    ),
    MoneyContainers.GOAL: IndexedContainerTarget(
        GOALS_INDEX,
        GOAL_PROGRESS_ADJUSTMENT_SCRIPT,
    ),
}


async def adjust_indexed_container_amount(
    container_id: str,
    kind: str,
    delta: Decimal,
) -> None:
    if not container_id or delta == 0:
        return

    target = _INDEXED_CONTAINERS.get(
        kind,
        _INDEXED_CONTAINERS[MoneyContainers.WALLET],
    )

    try:
        await get_elasticsearch().update(
            index=target.index_name,
            id=container_id,
            script={
                "source": target.adjustment_script,
                "lang": "painless",
                "params": {"delta": float(delta)},
            },
            retry_on_conflict=CONFLICT_RETRIES,
            refresh=SEARCHABLE_REFRESH,
        )
    except NotFoundError:
        log_container_amount_elastic_absent(container_id, target.index_name)
        return

    log_container_amount_elastic_adjusted(container_id, target.index_name, delta)


async def stored_container_kind(transaction_id: str) -> str:
    stored_kind = await (
        TransactionReadModel.objects.filter(id=transaction_id)
        .values_list("container_kind", flat=True)
        .afirst()
    )

    return stored_kind or MoneyContainers.WALLET


class AdjustContainerAmountOnCreate(Effect):
    async def apply(self, event: EventMessage) -> None:
        payload = decode_payload(event, TransactionCreated)
        await adjust_indexed_container_amount(
            payload.wallet_id,
            payload.container_kind or MoneyContainers.WALLET,
            Decimal(payload.amount),
        )

    async def compensate(self, event: EventMessage) -> None:
        payload = decode_payload(event, TransactionCreated)
        await adjust_indexed_container_amount(
            payload.wallet_id,
            payload.container_kind or MoneyContainers.WALLET,
            -Decimal(payload.amount),
        )


class AdjustContainerAmountOnUpdate(Effect):
    async def apply(self, event: EventMessage) -> None:
        payload = decode_payload(event, TransactionUpdated)
        await adjust_indexed_container_amount(
            payload.wallet_id,
            await stored_container_kind(payload.transaction_id),
            _updated_delta(payload),
        )

    async def compensate(self, event: EventMessage) -> None:
        payload = decode_payload(event, TransactionUpdated)
        await adjust_indexed_container_amount(
            payload.wallet_id,
            await stored_container_kind(payload.transaction_id),
            -_updated_delta(payload),
        )


class AdjustContainerAmountOnDelete(Effect):
    async def apply(self, event: EventMessage) -> None:
        payload = decode_payload(event, TransactionDeleted)
        await adjust_indexed_container_amount(
            payload.wallet_id,
            await stored_container_kind(payload.transaction_id),
            -Decimal(payload.amount),
        )

    async def compensate(self, event: EventMessage) -> None:
        payload = decode_payload(event, TransactionDeleted)
        await adjust_indexed_container_amount(
            payload.wallet_id,
            await stored_container_kind(payload.transaction_id),
            Decimal(payload.amount),
        )


def _updated_delta(payload: TransactionUpdated) -> Decimal:
    return Decimal(payload.new_amount) - Decimal(payload.previous_amount)
