from decimal import ROUND_HALF_UP, Decimal

MAX_RATE_FRACTION_DIGITS = 12
RATE_QUANTUM = Decimal(1).scaleb(-MAX_RATE_FRACTION_DIGITS)


def format_rate(rate: Decimal) -> str:
    quantized = rate.quantize(RATE_QUANTUM, rounding=ROUND_HALF_UP)

    return f"{quantized.normalize():f}"
