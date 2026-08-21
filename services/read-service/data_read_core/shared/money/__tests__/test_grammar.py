from decimal import Decimal

import pytest

from data_read_core.shared.http_contract import DetailCode, ValidationFailed
from data_read_core.shared.money import format_amount, money, parse_amount

USD, JPY = 2, 0


@pytest.mark.parametrize(
    ("amount", "decimals", "expected"),
    [
        (Decimal("50"), USD, "50.00"),
        (Decimal("50.5"), USD, "50.50"),
        (Decimal("90"), JPY, "90"),
        (Decimal("-12.30"), USD, "-12.30"),
        (Decimal("0"), USD, "0.00"),
        (Decimal("-0.00"), USD, "0.00"),
    ],
)
def test_amounts_are_emitted_at_the_currency_scale(amount, decimals, expected):
    assert format_amount(amount, decimals) == expected


def test_money_object_carries_amount_and_currency():
    assert money(Decimal("10000"), "USD", USD) == {"amount": "10000.00", "currency": "USD"}


@pytest.mark.parametrize(
    ("raw", "decimals"),
    [("50", USD), ("50.00", USD), ("50.5", USD), ("90", JPY), ("-12.30", USD), ("0", USD)],
)
def test_requests_may_send_fewer_fraction_digits_than_the_scale(raw, decimals):
    assert parse_amount(raw, decimals, "amount") == Decimal(raw)


def test_more_fraction_digits_than_the_currency_allows_is_rejected():
    """The server does not silently round money: which of 50.00 and 50.01 is
    right is the user's decision."""

    with pytest.raises(ValidationFailed) as failure:
        parse_amount("50.005", USD, "amount")

    assert failure.value.details[0].code is DetailCode.AMOUNT_PRECISION


@pytest.mark.parametrize("raw", [50.00, 50, True, None])
def test_json_numbers_are_rejected_rather_than_coerced(raw):
    """A client that regresses to numbers is caught at the boundary instead of
    losing precision quietly."""

    with pytest.raises(ValidationFailed) as failure:
        parse_amount(raw, USD, "amount")

    assert failure.value.details[0].code is DetailCode.AMOUNT_MALFORMED


@pytest.mark.parametrize("raw", ["1e3", "+50.00", "007.00", "1,000.00", " 50.00", "50.00 USD", ""])
def test_non_canonical_strings_are_rejected(raw):
    with pytest.raises(ValidationFailed) as failure:
        parse_amount(raw, USD, "amount")

    assert failure.value.details[0].code is DetailCode.AMOUNT_MALFORMED


def test_integer_part_beyond_eighteen_digits_is_out_of_range():
    with pytest.raises(ValidationFailed) as failure:
        parse_amount("1234567890123456789.00", USD, "amount")

    assert failure.value.details[0].code is DetailCode.AMOUNT_OUT_OF_RANGE


def test_failure_names_the_field_it_came_from():
    with pytest.raises(ValidationFailed) as failure:
        parse_amount("50.005", USD, "opening_balance")

    assert failure.value.details[0].field == "opening_balance"
