"""Valuing a dispatch in the book's currency.

The ledger is kept in USD whatever the transaction was spent in, so every leg
carries what it is worth in the book and the rate that got it there.
"""

from decimal import Decimal
from uuid import UUID

from ..booking import book_legs
from ..contracts import BOOK_CURRENCY, PostingLeg
from .fakes import FixedRates

ACCOUNT = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")


def _leg(amount: str, *, debit: bool = True, position: int = 0) -> PostingLeg:
    return PostingLeg(
        account_id=ACCOUNT,
        title="Groceries",
        debit=debit,
        amount=Decimal(amount),
        position=position,
        currency_code="JPY",
    )


async def test_a_leg_is_valued_at_the_rate_it_was_booked_at():
    booked = await book_legs(
        [_leg("125.00")],
        FixedRates(Decimal("0.0067")),
        transaction_currency="JPY",
    )

    assert booked[0].book_amount == Decimal("0.84")
    assert booked[0].conversion_rate == Decimal("0.0067")
    assert booked[0].book_currency == BOOK_CURRENCY


async def test_the_leg_keeps_what_the_transaction_said():
    """The booked value is added, not substituted: the ledger still records
    that the user spent 125 JPY."""

    booked = await book_legs(
        [_leg("125.00")], FixedRates(Decimal("0.0067")), transaction_currency="JPY"
    )

    assert booked[0].leg.amount == Decimal("125.00")
    assert booked[0].leg.currency_code == "JPY"


async def test_every_leg_of_one_dispatch_books_at_one_rate():
    """Two sides of the same money. Converting them independently could round
    them into an imbalance the ledger would then carry forever."""

    rates = FixedRates(Decimal("0.0067"))

    booked = await book_legs(
        [_leg("125.00", debit=True, position=0), _leg("125.00", debit=False, position=1)],
        rates,
        transaction_currency="JPY",
    )

    assert {leg.conversion_rate for leg in booked} == {Decimal("0.0067")}
    assert {leg.book_amount for leg in booked} == {Decimal("0.84")}
    assert rates.asked == [("JPY", BOOK_CURRENCY)]


async def test_a_transaction_already_in_the_book_currency_books_at_one():
    booked = await book_legs(
        [_leg("40.00")], FixedRates(Decimal("999")), transaction_currency="USD"
    )

    assert booked[0].conversion_rate == Decimal(1)
    assert booked[0].book_amount == Decimal("40.00")


async def test_a_transaction_with_no_known_currency_is_treated_as_the_book_currency():
    """Postings dispatched before currencies were recorded carry none. Booking
    them at 1 leaves their balances exactly where they already were, rather than
    restating history against a rate nobody recorded at the time."""

    booked = await book_legs([_leg("40.00")], FixedRates(Decimal("999")), transaction_currency="")

    assert booked[0].conversion_rate == Decimal(1)
    assert booked[0].book_amount == Decimal("40.00")


async def test_the_booked_amount_is_rounded_to_the_book_currency_s_minor_unit():
    booked = await book_legs(
        [_leg("1.00")], FixedRates(Decimal("0.005")), transaction_currency="JPY"
    )

    assert booked[0].book_amount == Decimal("0.01")
