from decimal import Decimal

import pytest
from rest_framework import serializers

from write_service.common.money import MoneyAmountField


class Body(serializers.Serializer):
    amount = MoneyAmountField()


def errors_for(value) -> list[str]:
    body = Body(data={"amount": value})
    assert not body.is_valid()

    return [error.code for error in body.errors["amount"]]


@pytest.mark.parametrize("raw", ["50", "50.00", "50.005", "-12.30", "0"])
def test_canonical_decimal_strings_are_accepted(raw):
    """Grammar and range are the serializer's job; the per-currency scale check
    happens once the wallet is loaded and its currency is known."""

    body = Body(data={"amount": raw})

    assert body.is_valid(), body.errors
    assert body.validated_data["amount"] == Decimal(raw)


@pytest.mark.parametrize("raw", [50, 50.0, True, ["50"], {"amount": "50"}])
def test_json_numbers_and_non_strings_are_rejected(raw):
    """A client that regresses to numbers is caught at the boundary rather than
    losing precision quietly."""

    assert "amount_malformed" in errors_for(raw)


def test_a_null_amount_is_a_missing_amount():
    """`null` is never a valid amount: an unknown or inapplicable value omits
    the whole field."""

    assert errors_for(None) == ["null"]


@pytest.mark.parametrize("raw", ["1e3", "+50.00", "007.00", "1,000.00", " 50", "50 USD", ""])
def test_non_canonical_strings_are_rejected(raw):
    assert "amount_malformed" in errors_for(raw)


def test_integer_part_beyond_eighteen_digits_is_out_of_range():
    assert "amount_out_of_range" in errors_for("1234567890123456789.00")
