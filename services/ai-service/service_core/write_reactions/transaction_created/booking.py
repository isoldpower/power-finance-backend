from collections.abc import Sequence
from decimal import ROUND_HALF_UP, Decimal

from .contracts import (
    BOOK_CURRENCY,
    BookedLeg,
    ExchangeRates,
    PostingLeg,
)

BOOK_EXPONENT = Decimal("0.01")


async def book_legs(
    legs: Sequence[PostingLeg],
    rates: ExchangeRates,
    *,
    transaction_currency: str,
) -> list[BookedLeg]:
    rate, _ = await rates.rate_between(
        transaction_currency or BOOK_CURRENCY,
        BOOK_CURRENCY,
    )

    return [
        BookedLeg(
            leg=leg,
            book_amount=_to_book(leg.amount, rate),
            conversion_rate=rate,
        )
        for leg in legs
    ]


def _to_book(amount: Decimal, rate: Decimal) -> Decimal:
    return (amount * rate).quantize(
        BOOK_EXPONENT,
        rounding=ROUND_HALF_UP,
    )
