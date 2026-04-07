from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4
from django.test import SimpleTestCase
from finances.domain.entities.wallet import Wallet
from finances.domain.value_objects.money import Money
from finances.domain.exceptions.money import CurrencyMismatchException, InsufficientFundsException


class WalletTests(SimpleTestCase):
    def setUp(self):
        self.user_id = 1
        self.wallet_id = uuid4()
        self.initial_balance = Money(amount=Decimal("100.00"), currency_code="USD")
        self.wallet = Wallet(
            id=self.wallet_id,
            user_id=self.user_id,
            name="Test Wallet",
            balance=self.initial_balance,
            credit=False,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            deleted_at=None
        )

    def test_deposit_money_happy_path(self):
        deposit_amount = Money(amount=Decimal("50.00"), currency_code="USD")
        self.wallet.deposit_money(deposit_amount)
        
        self.assertEqual(self.wallet.balance.amount, Decimal("150.00"))
        self.assertEqual(self.wallet.balance.currency_code, "USD")

    def test_deposit_money_currency_mismatch_raises_error(self):
        deposit_amount = Money(amount=Decimal("50.00"), currency_code="EUR")
        
        with self.assertRaises(CurrencyMismatchException):
            self.wallet.deposit_money(deposit_amount)

    def test_withdraw_money_happy_path(self):
        withdraw_amount = Money(amount=Decimal("30.00"), currency_code="USD")
        self.wallet.withdraw_money(withdraw_amount)
        
        self.assertEqual(self.wallet.balance.amount, Decimal("70.00"))
        self.assertEqual(self.wallet.balance.currency_code, "USD")

    def test_withdraw_money_insufficient_funds_raises_error(self):
        withdraw_amount = Money(amount=Decimal("150.00"), currency_code="USD")
        
        with self.assertRaises(InsufficientFundsException):
            self.wallet.withdraw_money(withdraw_amount)

    def test_withdraw_money_currency_mismatch_raises_error(self):
        withdraw_amount = Money(amount=Decimal("30.00"), currency_code="EUR")
        
        with self.assertRaises(CurrencyMismatchException):
            self.wallet.withdraw_money(withdraw_amount)
