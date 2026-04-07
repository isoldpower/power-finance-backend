from unittest.mock import MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone
from decimal import Decimal
from django.test import TestCase
from finances.application.use_cases.commands.delete_transaction import DeleteTransactionCommand, DeleteTransactionCommandHandler
from finances.application.dtos import TransactionDTO
from finances.domain.entities.transaction import Transaction, TransactionParticipant
from finances.domain.entities.transaction_type import TransactionType
from finances.domain.entities.expense_category import ExpenseCategory
from finances.domain.entities.wallet import Wallet
from finances.domain.value_objects.money import Money
from finances.application.interfaces import TransactionRepository, WalletRepository


class DeleteTransactionTests(TestCase):
    def setUp(self):
        self.trans_repo = MagicMock(spec=TransactionRepository)
        self.wallet_repo = MagicMock(spec=WalletRepository)
        
        # Patch registry to avoid DB hits during handler init
        self.registry_patcher = patch("finances.application.use_cases.commands.delete_transaction.get_repository_registry")
        self.mock_registry = self.registry_patcher.start()

        # Patch transaction methods
        self.atomic_patcher = patch("django.db.transaction.atomic")
        self.on_commit_patcher = patch("django.db.transaction.on_commit")
        self.mock_atomic = self.atomic_patcher.start()
        self.mock_on_commit = self.on_commit_patcher.start()
        self.mock_atomic.return_value.__enter__.return_value = None

        self.handler = DeleteTransactionCommandHandler(
            transaction_repository=self.trans_repo,
            wallet_repository=self.wallet_repo
        )
        self.user_id = 1
        self.transaction_id = uuid4()
        self.wallet_id = uuid4()
        
        self.wallet = Wallet(
            id=self.wallet_id,
            user_id=self.user_id,
            name="Test Wallet",
            balance=Money(amount=Decimal("100.00"), currency_code="USD"),
            credit=False,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            deleted_at=None
        )
        
        self.transaction = Transaction.from_persistence(
            id=self.transaction_id,
            sender=TransactionParticipant(wallet_id=self.wallet_id, money=Money(amount=Decimal("20.00"), currency_code="USD")),
            receiver=None,
            description="Expense",
            type=TransactionType.EXPENSE,
            category=ExpenseCategory.FOOD,
            created_at=datetime.now(timezone.utc)
        )

    def tearDown(self):
        self.registry_patcher.stop()
        self.atomic_patcher.stop()
        self.on_commit_patcher.stop()

    def test_delete_transaction_happy_path(self):
        command = DeleteTransactionCommand(
            transaction_id=str(self.transaction_id),
            user_id=self.user_id
        )
        
        self.trans_repo.get_user_transaction_by_id.return_value = self.transaction
        self.wallet_repo.get_user_wallet_for_update.return_value = self.wallet
        self.trans_repo.delete_transaction_by_id.return_value = self.transaction
        
        result = self.handler.handle(command)
        
        self.assertIsInstance(result, TransactionDTO)
        # Rollback should add 20 USD back to wallet
        self.assertEqual(self.wallet.balance.amount, Decimal("120.00"))
        
        self.wallet_repo.save_wallet.assert_called_once_with(self.wallet)
        self.trans_repo.delete_transaction_by_id.assert_called_once_with(self.transaction_id)

    def test_delete_transaction_unauthorized_raises_error(self):
        command = DeleteTransactionCommand(
            transaction_id=str(self.transaction_id),
            user_id=2 # Different user
        )
        
        self.trans_repo.get_user_transaction_by_id.side_effect = Exception("Not owned")
        
        with self.assertRaises(Exception):
            self.handler.handle(command)
