from decimal import Decimal

AMOUNT_KEY = "amount"
CURRENCY_KEY = "currency"


def format_amount(amount: Decimal, decimals: int) -> str:
    """Render at exactly `decimals` fraction digits, with no negative zero."""

    quantized = amount.quantize(Decimal(1).scaleb(-decimals))
    if quantized == 0:
        quantized = abs(quantized)

    return f"{quantized:f}"


def money(amount: Decimal, currency: str, decimals: int) -> dict[str, str]:
    return {AMOUNT_KEY: format_amount(amount, decimals), CURRENCY_KEY: currency}
