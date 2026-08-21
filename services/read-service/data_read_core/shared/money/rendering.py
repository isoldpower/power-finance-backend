from decimal import Decimal

from .currency_catalog import CURRENCY_CATALOG

AMOUNT_KEY = "amount"
CURRENCY_KEY = "currency"


def format_amount(amount: Decimal, decimals: int) -> str:
    """Render at exactly `decimals` fraction digits, with no negative zero."""
    quantized = amount.quantize(Decimal(1).scaleb(-decimals))
    if quantized == 0:
        quantized = abs(quantized)

    return f"{quantized:f}"


def money(amount: Decimal, currency: str, decimals: int) -> dict[str, str]:
    return {
        AMOUNT_KEY: format_amount(amount, decimals),
        CURRENCY_KEY: currency,
    }


async def amount_at_scale(amount: Decimal | str, currency: str | None) -> str:
    """Render a stored amount at its own currency's scale."""
    decimals = await CURRENCY_CATALOG.decimals_or_default(currency)

    return format_amount(Decimal(str(amount)), decimals)


async def money_at_scale(amount: Decimal | str, currency: str) -> dict[str, str]:
    decimals = await CURRENCY_CATALOG.decimals_or_default(currency)

    return money(
        Decimal(str(amount)),
        currency,
        decimals,
    )
