from data_read_core.shared.money import money_at_scale
from data_read_core.shared.pagination import Page

from ..dtos import AccountDTO, ChartFilters


async def present_one(account: AccountDTO) -> dict:
    return {
        "id": account.id,
        "group": account.group,
        "name": account.name,
        "money": await money_at_scale(
            account.balance_amount,
            account.currency,
        ),
        "created_at": account.created_at,
        "updated_at": account.updated_at,
    }


async def present_many(accounts: list[AccountDTO]) -> list[dict]:
    return [await present_one(account) for account in accounts]


async def present_meta(
    page: Page,
    filters: ChartFilters,
    groups: dict[str, int],
    cached: bool,
) -> dict:
    return {
        **page.meta(cached=cached),
        "lowbar": await _lowbar_at_scale(filters),
        "currency": filters.currency,
        "group": filters.group,
        "groups": groups,
    }


async def _lowbar_at_scale(filters: ChartFilters) -> str:
    rendered_lowbar = await money_at_scale(
        filters.lowbar,
        filters.currency,
    )

    return rendered_lowbar["amount"]
