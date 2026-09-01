from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from django.db.models import DecimalField, F, FloatField, Q, Sum
from django.db.models.functions import Cast, Extract, Floor

from data_read_core.shared.postgres_orm import (
    AccountDispatchReadModel,
    AccountReadModel,
    TransactionReadModel,
)

CurrencyTotals = dict[str, Decimal]
BucketedTotals = dict[int, CurrencyTotals]
GroupSubtotals = dict[str, CurrencyTotals]
ZERO = Decimal(0)


@dataclass(frozen=True)
class TransactionAggregate:
    before: CurrencyTotals = field(default_factory=dict)
    window_total: CurrencyTotals = field(default_factory=dict)
    window_inflow: CurrencyTotals = field(default_factory=dict)
    window_outflow: CurrencyTotals = field(default_factory=dict)

    @property
    def currencies(self) -> list[str]:
        return [
            *self.before,
            *self.window_total,
            *self.window_inflow,
            *self.window_outflow,
        ]


def _owned_queryset(user_id: int):
    return TransactionReadModel.objects.filter(
        user_id=user_id,
        deleted_at__isnull=True,
    )


def _decimal_sum(condition: Q | None = None) -> Sum:
    return Sum(
        "amount",
        filter=condition,
        output_field=DecimalField(max_digits=20, decimal_places=2),
    )


async def aggregate_transactions(
    user_id: int,
    since: datetime | None,
    *,
    needs_window_total: bool,
    needs_flows: bool,
) -> TransactionAggregate:
    in_window = Q(created_at__gte=since) if since is not None else Q()
    unchained_aggregate = Q(chain_id__isnull=True)

    annotations_dict = {}
    if since is not None:
        annotations_dict["before"] = _decimal_sum(
            Q(created_at__lt=since),
        )
    if needs_window_total:
        annotations_dict["window_total"] = _decimal_sum(in_window)
    if needs_flows:
        annotations_dict["window_inflow"] = _decimal_sum(
            in_window & unchained_aggregate & Q(amount__gt=0),
        )
        annotations_dict["window_outflow"] = _decimal_sum(
            in_window & unchained_aggregate & Q(amount__lt=0),
        )

    if not annotations_dict:
        return TransactionAggregate()

    transaction_rows = _owned_queryset(user_id).values("currency_code").annotate(**annotations_dict)

    collected: dict[str, CurrencyTotals] = defaultdict(dict)
    async for transaction in transaction_rows:
        currency = transaction["currency_code"]
        for name in annotations_dict:
            collected[name][currency] = transaction[name] or ZERO

    return TransactionAggregate(
        before=collected.get("before", {}),
        window_total=collected.get("window_total", {}),
        window_inflow=collected.get("window_inflow", {}),
        window_outflow={
            currency: -total for currency, total in collected.get("window_outflow", {}).items()
        },
    )


async def sum_by_bucket(
    user_id: int,
    time_since: datetime,
    time_until: datetime,
    points_count: int,
) -> BucketedTotals:
    width_seconds = max((time_until - time_since).total_seconds() / points_count, 1e-9)
    time_position = Cast(Extract("created_at", "epoch"), FloatField()) - time_since.timestamp()
    bucket_number = Floor(time_position / width_seconds)

    transaction_rows = (
        _owned_queryset(user_id)
        .filter(created_at__gte=time_since, created_at__lt=time_until)
        .annotate(bucket=bucket_number)
        .values("bucket", "currency_code")
        .annotate(total=_decimal_sum())
    )

    bucketed_totals: BucketedTotals = defaultdict(dict)
    async for transaction in transaction_rows:
        index = min(
            int(transaction["bucket"]),
            points_count - 1,
        )
        currency = transaction["currency_code"]
        current_total = bucketed_totals[index].get(currency, ZERO)
        bucketed_totals[index][currency] = current_total + (transaction["total"] or ZERO)

    return dict(bucketed_totals)


async def earliest_transaction_at(user_id: int) -> datetime | None:
    first_transaction = await _owned_queryset(user_id).order_by(F("created_at").asc()).afirst()

    return first_transaction.created_at if first_transaction else None


async def sum_accounts_by_group_and_currency(user_id: int) -> GroupSubtotals:
    account_rows = (
        AccountReadModel.objects.filter(user_id=user_id)
        .values("group", "currency_code")
        .annotate(total=Sum("balance"))
    )

    group_subtotals: GroupSubtotals = defaultdict(dict)
    async for account in account_rows:
        group_subtotals[account["group"]][account["currency_code"]] = account["total"] or ZERO

    return dict(group_subtotals)


async def count_unbalanced_dispatches(user_id: int) -> int:
    return await AccountDispatchReadModel.objects.filter(
        user_id=user_id,
        balanced=False,
    ).acount()
