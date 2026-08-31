from dataclasses import dataclass
from decimal import Decimal

from .posting_leg import PostingLeg

BOOK_CURRENCY = "USD"


@dataclass(frozen=True, slots=True)
class BookedLeg:
    leg: PostingLeg
    book_amount: Decimal
    conversion_rate: Decimal
    book_currency: str = BOOK_CURRENCY
