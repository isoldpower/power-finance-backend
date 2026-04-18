from unittest.mock import MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone
from decimal import Decimal
from django.test import SimpleTestCase
from finances.application.use_cases.queries.get_transaction import GetTransactionQuery, GetTransactionQueryHandler
from finances.application.dtos import TransactionDTO
from finances.domain.entities.old_transaction import Transaction, TransactionParticipant
from finances.domain.entities.transaction_type import TransactionType
from finances.domain.entities.expense_category import ExpenseCategory
from finances.domain.entities.wallet import Wallet
from finances.domain.value_objects.money import Money
from finances.application.interfaces import TransactionRepository, WalletRepository


class GetTransactionTests(SimpleTestCase):
    def setUp(self):
        self.trans_repo = MagicMock(spec=TransactionRepository)
        self.wallet_repo = MagicMock(spec=WalletRepository)
        
        # Patch registry to avoid DB hits during handler init
        self.registry_patcher = patch("finances.application.use_cases.queries.get_transaction.get_repository_registry")
        self.mock_registry = self.registry_patcher.start()
        
        self.handler = GetTransactionQueryHandler(
            transaction_repository=self.trans_repo,
            wallet_repository=self.wallet_repo
        )
        self.user_id = 1
        self.transaction_id = uuid4()
        self.wallet_id = uuid4()

    def tearDown(self):
        self.registry_patcher.stop()

    def test_get_transaction_fetches_single_transaction_and_wallets(self):
        query = GetTransactionQuery(user_id=self.user_id, transaction_id=str(self.transaction_id))
        
        mock_transaction = Transaction.from_persistence(
            id=self.transaction_id,
            sender=TransactionParticipant(wallet_id=self.wallet_id, money=Money(Decimal("10.00"), "USD")),
            receiver=None,
            description="Test",
            type=TransactionType.EXPENSE,
            category=ExpenseCategory.FOOD,
            created_at=datetime.now(timezone.utc)
        )
        
        mock_wallet = Wallet(
            id=self.wallet_id,
            user_id=self.user_id,
            name="Test Wallet",
            balance=Money(Decimal("100.00"), "USD"),
            credit=False,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            deleted_at=None
        )
        
        self.trans_repo.get_user_transaction_by_id.return_value = mock_transaction
        self.wallet_repo.get_user_wallet_by_id.return_value = mock_wallet
        
        result = self.handler.handle(query)
        
        self.assertIsInstance(result, TransactionDTO)
        self.assertEqual(result.id, self.transaction_id)
        self.assertEqual(result.sender.wallet.id, self.wallet_id)
        
        self.trans_repo.get_user_transaction_by_id.assert_called_once_with(self.user_id, self.transaction_id)
        self.wallet_repo.get_user_wallet_by_id.assert_called_once_with(self.wallet_id, self.user_id)
