from decimal import Decimal

import pytest

from data_read_core.shared.exchange_rates import format_rate


@pytest.mark.parametrize(
    ("rate", "expected"),
    [
        (Decimal("82"), "82"),
        (Decimal("82.00"), "82"),
        (Decimal("0.90"), "0.9"),
        (Decimal("1"), "1"),
        (Decimal("0"), "0"),
        (Decimal("100"), "100"),
        (Decimal("1E+2"), "100"),
        (Decimal("0.000000000001"), "0.000000000001"),
    ],
)
def test_rates_are_unpadded_and_never_in_exponent_form(rate, expected):
    assert format_rate(rate) == expected


def test_rates_are_cut_to_twelve_fraction_digits():
    assert format_rate(Decimal("0.0000000000004")) == "0"
    assert format_rate(Decimal("1.2345678901239")) == "1.234567890124"
