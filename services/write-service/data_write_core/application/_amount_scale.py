from decimal import Decimal

from data_write_core.domain.exceptions import (
    AmountPrecisionError,
    InvalidTransactionAmountError,
)

from .money_scales import decimals_for


async def ensure_amount_scale(amount: Decimal, currency_code: str) -> None:
    decimals = await decimals_for(currency_code)
    exponent = amount.as_tuple().exponent

    # A non-integer exponent means NaN or Infinity. The request grammar rejects
    # both long before this, so it can only arrive from code constructing a
    # command by hand — and a ledger is the last place to let one through.
    if not isinstance(exponent, int):
        raise InvalidTransactionAmountError(amount)

    fraction_digits = max(0, -exponent)
    if fraction_digits > decimals:
        raise AmountPrecisionError(amount, currency_code, decimals)
