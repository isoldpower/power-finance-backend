from decimal import Decimal

from data_write_core.domain.exceptions import (
    AmountPrecisionError,
    InvalidTransactionAmountError,
)

from .money_scales import decimals_for


async def ensure_amount_scale(amount: Decimal, currency_code: str) -> None:
    decimals = await decimals_for(currency_code)
    exponent = amount.as_tuple().exponent

    if not isinstance(exponent, int):
        raise InvalidTransactionAmountError(amount)

    fraction_digits = max(0, -exponent)
    if fraction_digits > decimals:
        raise AmountPrecisionError(amount, currency_code, decimals)
