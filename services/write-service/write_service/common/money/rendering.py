from decimal import Decimal

from write_service.common.money.config import MoneyKey


def format_amount(amount: Decimal, decimals: int) -> str:
    quantized = amount.quantize(Decimal(1).scaleb(-decimals))
    if quantized == 0:
        quantized = abs(quantized)

    return f"{quantized:f}"


def money(amount: Decimal, currency: str, decimals: int) -> dict[str, str]:
    return {MoneyKey.AMOUNT: format_amount(amount, decimals), MoneyKey.CURRENCY: currency}
