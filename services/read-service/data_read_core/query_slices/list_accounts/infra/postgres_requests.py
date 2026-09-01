from decimal import Decimal

from django.db.models import Count, Q

from data_read_core.shared.pagination import PageRequest, apply_keyset
from data_read_core.shared.postgres_orm import AccountGroups, AccountReadModel

from ..dtos import ALL_GROUPS, ChartFilters

Thresholds = dict[str, Decimal]


def _owned_queryset(user_id: int, filters: ChartFilters, thresholds: Thresholds | None):
    queryset = AccountReadModel.objects.filter(user_id=user_id)
    if filters.narrows_by_group:
        queryset = queryset.filter(group=filters.group)

    return _above_thresholds(queryset, thresholds)


def _above_thresholds(queryset, thresholds: Thresholds | None):
    if thresholds is None:
        return queryset

    if not thresholds:
        return queryset.none()

    predicate = Q()
    for currency_code, minimum in thresholds.items():
        predicate |= Q(currency_code=currency_code) & (
            Q(balance__gte=minimum) | Q(balance__lte=-minimum)
        )

    return queryset.filter(predicate)


async def fetch_owned_accounts(
    user_id: int,
    page: PageRequest,
    filters: ChartFilters,
    thresholds: Thresholds | None,
) -> list[AccountReadModel]:
    queryset = apply_keyset(
        _owned_queryset(user_id, filters, thresholds),
        page,
    )

    return [account async for account in queryset]


async def count_owned_accounts(
    user_id: int,
    filters: ChartFilters,
    thresholds: Thresholds | None,
) -> int:
    return await _owned_queryset(user_id, filters, thresholds).acount()


async def count_accounts_by_group(
    user_id: int,
    filters: ChartFilters,
    thresholds: Thresholds | None,
) -> dict[str, int]:
    across_every_group = ChartFilters(
        group=ALL_GROUPS,
        lowbar=filters.lowbar,
        currency=filters.currency,
    )
    account_rows = (
        _owned_queryset(user_id, across_every_group, thresholds)
        .values("group")
        .annotate(total=Count("id"))
    )

    counted = {group.value: 0 for group in AccountGroups}
    async for account in account_rows:
        if account["group"] in counted:
            counted[account["group"]] = account["total"]

    return counted


async def distinct_account_currencies(user_id: int) -> list[str]:
    return [
        currency_code
        async for currency_code in (
            AccountReadModel.objects.filter(user_id=user_id)
            .values_list("currency_code", flat=True)
            .distinct()
        )
    ]
