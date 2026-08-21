"""A rate is a string, but it is not money: it carries no currency, so it has no
scale to pad to. Trailing zeros are trimmed rather than added."""

from decimal import ROUND_HALF_UP, Decimal

MAX_RATE_FRACTION_DIGITS = 12
RATE_QUANTUM = Decimal(1).scaleb(-MAX_RATE_FRACTION_DIGITS)


def format_rate(rate: Decimal) -> str:
    """Render at up to 12 fraction digits, unpadded and never in exponent form."""

    quantized = rate.quantize(RATE_QUANTUM, rounding=ROUND_HALF_UP)

    return f"{quantized.normalize():f}"
