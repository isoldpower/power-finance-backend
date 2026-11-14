from decimal import ROUND_HALF_UP, Decimal

from .config import HUNDRED, PERCENTAGE_EXPONENT, ZERO


def share_of(part: Decimal, total: Decimal) -> Decimal:
    if total == 0:
        return ZERO

    return _rounded(part / total * HUNDRED)


def change_between(current: Decimal, previous: Decimal) -> Decimal | None:
    if previous == 0:
        return None

    return _rounded((current - previous) / previous * HUNDRED)


def savings_rate_of(inflow: Decimal, outflow: Decimal) -> Decimal | None:
    if inflow == 0:
        return None

    return _rounded((inflow - outflow) / inflow * HUNDRED)


def _rounded(percentage: Decimal) -> Decimal:
    return percentage.quantize(PERCENTAGE_EXPONENT, rounding=ROUND_HALF_UP)
