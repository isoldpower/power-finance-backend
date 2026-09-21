from dataclasses import dataclass
from decimal import Decimal

from django.db.models import F

from data_read_core.shared.postgres_orm import (
    GoalReadModel,
    MoneyContainers,
    WalletReadModel,
)


@dataclass(frozen=True)
class ContainerLabel:
    currency_code: str
    name: str
    kind: str


async def _container_currency(container_id: str) -> str:
    return (await _container_label(container_id)).currency_code


async def _container_label(
    container_id: str,
    kind: str | None = None,
) -> ContainerLabel:
    if kind != MoneyContainers.GOAL:
        wallet = await (
            WalletReadModel.objects.filter(id=container_id)
            .values_list("currency_code", "title")
            .afirst()
        )
        if wallet is not None:
            return ContainerLabel(
                currency_code=wallet[0] or "",
                name=wallet[1] or "",
                kind=MoneyContainers.WALLET,
            )
        if kind == MoneyContainers.WALLET:
            return ContainerLabel(
                currency_code="",
                name="",
                kind=MoneyContainers.WALLET,
            )

    first_stored = await (
        GoalReadModel.objects.filter(id=container_id).values_list("currency_code", "title").afirst()
    )
    if first_stored is not None:
        return ContainerLabel(
            currency_code=first_stored[0] or "",
            name=first_stored[1] or "",
            kind=MoneyContainers.GOAL,
        )

    return ContainerLabel(
        currency_code="",
        name="",
        kind=kind or MoneyContainers.WALLET,
    )


async def apply_container_delta(
    container_id,
    kind: str,
    amount: Decimal,
) -> int:
    if kind == MoneyContainers.GOAL:
        return await GoalReadModel.objects.filter(id=container_id).aupdate(
            progress=F("progress") + amount
        )

    return await WalletReadModel.objects.filter(id=container_id).aupdate(
        balance=F("balance") + amount
    )
