"""Money / NonNegativeMoney arithmetic and currency-binding rules: cross-currency
ops raise, negative NonNegativeMoney is rejected, precision is preserved."""

from __future__ import annotations

from decimal import Decimal

from django.test import SimpleTestCase

from data_write_core.domain.exceptions import (
    CurrencyMismatchError,
    NegativeMoneyError,
)
from data_write_core.domain.value_objects.money import Money, NonNegativeMoney


class MoneyArithmeticTests(SimpleTestCase):
    def test_addition_within_same_currency_sums_amounts(self) -> None:
        result = Money(Decimal("10.50"), "USD") + Money(Decimal("4.25"), "USD")

        self.assertEqual(result, Money(Decimal("14.75"), "USD"))

    def test_subtraction_within_same_currency_subtracts_amounts(self) -> None:
        result = Money(Decimal("10.00"), "USD") - Money(Decimal("3.75"), "USD")

        self.assertEqual(result, Money(Decimal("6.25"), "USD"))

    def test_subtraction_can_produce_negative_amount(self) -> None:
        result = Money(Decimal("1"), "USD") - Money(Decimal("5"), "USD")

        self.assertEqual(result.amount, Decimal("-4"))
        self.assertEqual(result.currency_code, "USD")

    def test_addition_across_currencies_raises(self) -> None:
        with self.assertRaises(CurrencyMismatchError) as ctx:
            _ = Money(Decimal("1"), "USD") + Money(Decimal("1"), "EUR")

        self.assertEqual(ctx.exception.from_currency, "USD")
        self.assertEqual(ctx.exception.to_currency, "EUR")

    def test_subtraction_across_currencies_raises(self) -> None:
        with self.assertRaises(CurrencyMismatchError) as ctx:
            _ = Money(Decimal("1"), "USD") - Money(Decimal("1"), "EUR")

        self.assertEqual(ctx.exception.from_currency, "USD")
        self.assertEqual(ctx.exception.to_currency, "EUR")

    def test_decimal_precision_is_preserved_across_operations(self) -> None:
        result = Money(Decimal("0.1"), "USD") + Money(Decimal("0.2"), "USD")

        self.assertEqual(result.amount, Decimal("0.3"))

    def test_money_is_value_equal_when_amount_and_currency_match(self) -> None:
        self.assertEqual(Money(Decimal("5"), "USD"), Money(Decimal("5"), "USD"))

    def test_money_is_value_unequal_when_currency_differs(self) -> None:
        self.assertNotEqual(Money(Decimal("5"), "USD"), Money(Decimal("5"), "EUR"))

    def test_money_is_hashable_and_usable_in_sets(self) -> None:
        self.assertEqual(
            {Money(Decimal("1"), "USD"), Money(Decimal("1"), "USD")},
            {Money(Decimal("1"), "USD")},
        )

    def test_str_renders_amount_then_currency(self) -> None:
        self.assertEqual(str(Money(Decimal("12.34"), "USD")), "12.34 USD")


class NonNegativeMoneyTests(SimpleTestCase):
    def test_zero_amount_is_allowed(self) -> None:
        money = NonNegativeMoney(Decimal("0"), "USD")

        self.assertEqual(money.amount, Decimal("0"))

    def test_positive_amount_is_allowed(self) -> None:
        money = NonNegativeMoney(Decimal("100"), "USD")

        self.assertEqual(money.amount, Decimal("100"))

    def test_negative_amount_raises_at_construction(self) -> None:
        with self.assertRaises(NegativeMoneyError) as ctx:
            NonNegativeMoney(Decimal("-0.01"), "USD")

        self.assertEqual(ctx.exception.amount, Decimal("-0.01"))

    def test_non_negative_money_inherits_money_arithmetic(self) -> None:
        result = NonNegativeMoney(Decimal("3"), "USD") + NonNegativeMoney(Decimal("2"), "USD")

        self.assertIsInstance(result, Money)
        self.assertEqual(result.amount, Decimal("5"))
