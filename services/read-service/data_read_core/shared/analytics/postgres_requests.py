from collections.abc import Collection
from datetime import datetime
from decimal import Decimal
from typing import NamedTuple

from django.db.models import DecimalField, Max, Min, Sum

from data_read_core.shared.postgres_orm import (
    MoneyContainers,
    TransactionReadModel,
    WalletReadModel,
)

from .config import ZERO, LedgerSide
from .ledger_rows import LedgerRow, LedgerWallet

LEDGER_ROW_COLUMNS = (
    "id",
    "wallet_id",
    "amount",
    "currency_code",
    "name",
    "category",
    "chain_id",
    "created_at",
)


class TransactionTimeBounds(NamedTuple):
    first_transaction_at: datetime | None
    last_transaction_at: datetime | None


def _wallet_ledger_queryset(user_id: int, wallet_identifiers: Collection[str]):
    return TransactionReadModel.objects.filter(
        user_id=user_id,
        deleted_at__isnull=True,
        container_kind=MoneyContainers.WALLET,
        wallet_id__in=list(wallet_identifiers),
    )


async def fetch_open_wallets(user_id: int) -> list[LedgerWallet]:
    wallet_rows = WalletReadModel.objects.filter(
        user_id=user_id,
        deleted_at__isnull=True,
    ).values("id", "title", "color", "currency_code", "favorite")

    open_wallets = [
        LedgerWallet(
            identifier=str(wallet_row["id"]),
            name=wallet_row["title"],
            color=wallet_row["color"],
            currency=wallet_row["currency_code"],
            favorite=wallet_row["favorite"],
        )
        async for wallet_row in wallet_rows
    ]

    return sorted(
        open_wallets,
        key=lambda wallet: (not wallet.favorite, wallet.name.casefold(), wallet.name),
    )


async def fetch_ledger_rows(
    user_id: int,
    wallet_currencies: dict[str, str],
    since: datetime,
    until: datetime,
    *,
    include_balance_movements: bool,
    include_until: bool = False,
) -> list[LedgerRow]:
    if not wallet_currencies:
        return []

    queryset = _wallet_ledger_queryset(user_id, wallet_currencies).filter(created_at__gte=since)
    queryset = (
        queryset.filter(created_at__lte=until)
        if include_until
        else queryset.filter(created_at__lt=until)
    )
    if not include_balance_movements:
        queryset = queryset.filter(chain_id__isnull=True, is_opening_balance=False)

    transaction_rows = queryset.order_by("created_at", "id").values(*LEDGER_ROW_COLUMNS)

    return [
        _ledger_row_from(transaction_row, wallet_currencies)
        async for transaction_row in transaction_rows
    ]


async def sum_native_balances_before(
    user_id: int,
    wallet_identifiers: Collection[str],
    instant: datetime,
) -> dict[str, Decimal]:
    if not wallet_identifiers:
        return {}

    balance_rows = (
        _wallet_ledger_queryset(user_id, wallet_identifiers)
        .filter(created_at__lt=instant)
        .values("wallet_id")
        .annotate(
            total=Sum(
                "amount",
                output_field=DecimalField(max_digits=20, decimal_places=2),
            )
        )
    )

    return {
        str(balance_row["wallet_id"]): balance_row["total"] or ZERO
        async for balance_row in balance_rows
    }


async def fetch_category_vocabulary(
    user_id: int,
    wallet_identifiers: Collection[str],
) -> dict[LedgerSide, list[str]]:
    categorised = _wallet_ledger_queryset(user_id, wallet_identifiers).filter(
        chain_id__isnull=True,
        is_opening_balance=False,
        category__isnull=False,
    )

    return {
        LedgerSide.EXPENSE: await _distinct_categories(categorised.filter(amount__lt=0)),
        LedgerSide.INCOME: await _distinct_categories(categorised.filter(amount__gt=0)),
    }


async def fetch_transaction_time_bounds(
    user_id: int,
    wallet_identifiers: Collection[str],
) -> TransactionTimeBounds:
    if not wallet_identifiers:
        return TransactionTimeBounds(first_transaction_at=None, last_transaction_at=None)

    bounds = await _wallet_ledger_queryset(user_id, wallet_identifiers).aaggregate(
        first_transaction_at=Min("created_at"),
        last_transaction_at=Max("created_at"),
    )

    return TransactionTimeBounds(
        first_transaction_at=bounds["first_transaction_at"],
        last_transaction_at=bounds["last_transaction_at"],
    )


async def _distinct_categories(queryset) -> list[str]:
    category_names = {
        category_name
        async for category_name in queryset.values_list("category", flat=True).distinct()
    }

    return sorted(
        category_names, key=lambda category_name: (category_name.casefold(), category_name)
    )


def _ledger_row_from(transaction_row: dict, wallet_currencies: dict[str, str]) -> LedgerRow:
    wallet_identifier = str(transaction_row["wallet_id"])
    chain_identifier = transaction_row["chain_id"]

    return LedgerRow(
        identifier=str(transaction_row["id"]),
        wallet_identifier=wallet_identifier,
        signed_amount=transaction_row["amount"],
        currency=transaction_row["currency_code"] or wallet_currencies[wallet_identifier],
        name=transaction_row["name"],
        category=transaction_row["category"],
        chain_identifier=str(chain_identifier) if chain_identifier else None,
        created_at=transaction_row["created_at"],
    )
