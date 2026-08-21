from decimal import Decimal

from write_service.common.http_contract import UnsupportedCurrency
from write_service.common.money import format_amount, money

from .bootstrap import get_repository_registry

DEFAULT_DECIMALS = 2
_cache: dict[str, int] = {}


async def load_scales() -> dict[str, int]:
    global _cache

    if not _cache:
        _cache = await get_repository_registry().currency_repository.get_decimals_by_code()

    return _cache


def reset_scale_cache() -> None:
    global _cache
    _cache = {}


async def decimals_for(currency_code: str) -> int:
    decimals = (await load_scales()).get(currency_code.upper())
    if decimals is None:
        raise UnsupportedCurrency(f"Currency {currency_code!r} is not supported")

    return decimals


async def decimals_or_default(currency_code: str | None) -> int:
    if not currency_code:
        return DEFAULT_DECIMALS

    return (await load_scales()).get(
        currency_code.upper(),
        DEFAULT_DECIMALS,
    )


async def amount_at_scale(amount: Decimal | str, currency_code: str | None) -> str:
    return format_amount(
        Decimal(str(amount)),
        await decimals_or_default(currency_code),
    )


async def money_at_scale(amount: Decimal | str, currency_code: str) -> dict[str, str]:
    decimals = await decimals_or_default(currency_code)

    return money(Decimal(str(amount)), currency_code, decimals)
