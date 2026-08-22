from datetime import datetime
from decimal import Decimal

from django.db.models import Q, Sum

from data_read_core.shared.pagination import PageRequest, apply_keyset
from data_read_core.shared.postgres_orm import TransactionReadModel, WalletReadModel


async def fetch_owned_wallet(user_id: int, wallet_id: str) -> WalletReadModel | None:
    return await WalletReadModel.objects.filter(
        id=wallet_id,
        user_id=user_id,
    ).afirst()


async def sum_wallet_flows(
    wallet_id: str,
    since: datetime | None,
    until: datetime | None,
) -> tuple[Decimal, Decimal]:
    window: dict[str, datetime] = {}
    if since is not None:
        window["occurred_at__gte"] = since
    if until is not None:
        window["occurred_at__lt"] = until

    totals = await TransactionReadModel.objects.filter(
        wallet_id=wallet_id,
        **window,
    ).aaggregate(
        inflow=Sum("amount", filter=Q(amount__gt=0)),
        outflow=Sum("amount", filter=Q(amount__lt=0)),
    )

    return (
        totals["inflow"] or Decimal("0"),
        -(totals["outflow"] or Decimal("0")),
    )


def recent_transactions_queryset(wallet_id: str):
    return TransactionReadModel.objects.filter(
        wallet_id=wallet_id,
        deleted_at__isnull=True,
    )


async def fetch_recent_transactions(
    wallet_id: str,
    page: PageRequest,
) -> list[TransactionReadModel]:
    queryset = apply_keyset(recent_transactions_queryset(wallet_id), page)

    return [transaction async for transaction in queryset]


async def count_recent_transactions(wallet_id: str) -> int:
    return await recent_transactions_queryset(wallet_id).acount()
