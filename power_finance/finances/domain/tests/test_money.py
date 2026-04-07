from decimal import Decimal
from django.test import SimpleTestCase
from finances.domain.value_objects.money import Money


class MoneyTests(SimpleTestCase):
    def test_str_format(self):
        amount = Decimal("100.50")
        currency = "USD"
        money = Money(amount=amount, currency_code=currency)
        
        self.assertEqual(str(money), "100.50 USD")

    def test_add_same_currency(self):
        money_1 = Money(amount=Decimal("100.00"), currency_code="USD")
        money_2 = Money(amount=Decimal("50.00"), currency_code="USD")
        
        result = money_1 + money_2
        
        self.assertEqual(result.amount, Decimal("150.00"))
        self.assertEqual(result.currency_code, "USD")

    def test_add_different_currency_raises_error(self):
        money_1 = Money(amount=Decimal("100.00"), currency_code="USD")
        money_2 = Money(amount=Decimal("50.00"), currency_code="EUR")
        
        with self.assertRaisesMessage(ValueError, "Currency mismatch"):
            _ = money_1 + money_2

    def test_sub_same_currency(self):
        money_1 = Money(amount=Decimal("100.00"), currency_code="USD")
        money_2 = Money(amount=Decimal("30.00"), currency_code="USD")
        
        result = money_1 - money_2
        
        self.assertEqual(result.amount, Decimal("70.00"))
        self.assertEqual(result.currency_code, "USD")

    def test_sub_different_currency_raises_error(self):
        money_1 = Money(amount=Decimal("100.00"), currency_code="USD")
        money_2 = Money(amount=Decimal("50.00"), currency_code="EUR")
        
        with self.assertRaisesMessage(ValueError, "Currency mismatch"):
            _ = money_1 - money_2
