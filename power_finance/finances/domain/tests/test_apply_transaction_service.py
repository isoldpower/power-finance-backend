from decimal import Decimal
from uuid import uuid4
from datetime import datetime, timezone
from django.test import SimpleTestCase
from finances.domain.entities.old_transaction import Transaction, TransactionParticipant
from finances.domain.entities.wallet import Wallet
from finances.domain.entities.transaction_type import TransactionType
from finances.domain.entities.expense_category import ExpenseCategory
from finances.domain.value_objects.money import Money
from finances.domain.services.apply_transaction_to_wallet import (
    apply_transaction_to_wallet_balance,
    rollback_transaction_from_wallet_balance
)


class ApplyTransactionServiceTests(SimpleTestCase):
    def setUp(self):
        self.user_id = 1
        self.wallet_id_sender = uuid4()
        self.wallet_id_receiver = uuid4()
        
        self.sender_wallet = Wallet(
            id=self.wallet_id_sender,
            user_id=self.user_id,
            name="Sender Wallet",
            balance=Money(amount=Decimal("100.00"), currency_code="USD"),
            credit=False,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            deleted_at=None
        )
        
        self.receiver_wallet = Wallet(
            id=self.wallet_id_receiver,
            user_id=self.user_id,
            name="Receiver Wallet",
            balance=Money(amount=Decimal("50.00"), currency_code="USD"),
            credit=False,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            deleted_at=None
        )

    def test_apply_transaction_withdraws_from_sender_deposits_to_receiver(self):
        amount = Money(amount=Decimal("30.00"), currency_code="USD")
        transaction = Transaction.create(
            sender=TransactionParticipant(wallet_id=self.wallet_id_sender, money=amount),
            receiver=TransactionParticipant(wallet_id=self.wallet_id_receiver, money=amount),
            description="Transfer",
            type=TransactionType.TRANSFER,
            category=ExpenseCategory.FOOD
        )
        
        apply_transaction_to_wallet_balance(
            transaction=transaction,
            sender_wallet=self.sender_wallet,
            receiver_wallet=self.receiver_wallet
        )
        
        self.assertEqual(self.sender_wallet.balance.amount, Decimal("70.00"))
        self.assertEqual(self.receiver_wallet.balance.amount, Decimal("80.00"))

    def test_apply_transaction_no_sender_wallet_no_withdrawal(self):
        amount = Money(amount=Decimal("30.00"), currency_code="USD")
        transaction = Transaction.create(
            sender=None,
            receiver=TransactionParticipant(wallet_id=self.wallet_id_receiver, money=amount),
            description="Income",
            type=TransactionType.INCOME,
            category=ExpenseCategory.FOOD
        )
        
        apply_transaction_to_wallet_balance(
            transaction=transaction,
            sender_wallet=None,
            receiver_wallet=self.receiver_wallet
        )
        
        self.assertEqual(self.receiver_wallet.balance.amount, Decimal("80.00"))

    def test_apply_transaction_no_receiver_wallet_no_deposit(self):
        amount = Money(amount=Decimal("30.00"), currency_code="USD")
        transaction = Transaction.create(
            sender=TransactionParticipant(wallet_id=self.wallet_id_sender, money=amount),
            receiver=None,
            description="Expense",
            type=TransactionType.EXPENSE,
            category=ExpenseCategory.FOOD
        )
        
        apply_transaction_to_wallet_balance(
            transaction=transaction,
            sender_wallet=self.sender_wallet,
            receiver_wallet=None
        )
        
        self.assertEqual(self.sender_wallet.balance.amount, Decimal("70.00"))

    def test_rollback_transaction_deposits_to_sender_withdraws_from_receiver(self):
        amount = Money(amount=Decimal("30.00"), currency_code="USD")
        transaction = Transaction.create(
            sender=TransactionParticipant(wallet_id=self.wallet_id_sender, money=amount),
            receiver=TransactionParticipant(wallet_id=self.wallet_id_receiver, money=amount),
            description="Transfer",
            type=TransactionType.TRANSFER,
            category=ExpenseCategory.FOOD
        )
        
        rollback_transaction_from_wallet_balance(
            transaction=transaction,
            sender_wallet=self.sender_wallet,
            receiver_wallet=self.receiver_wallet
        )
        
        self.assertEqual(self.sender_wallet.balance.amount, Decimal("130.00"))
        self.assertEqual(self.receiver_wallet.balance.amount, Decimal("20.00"))
