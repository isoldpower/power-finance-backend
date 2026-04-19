from unittest.mock import MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone
from decimal import Decimal
from django.test import SimpleTestCase
from finances.application.use_cases.queries.list_transactions import ListTransactionsQuery, ListTransactionsQueryHandler
from finances.application.dtos import TransactionPlainDTO
from finances.domain.entities.old_transaction import Transaction, TransactionParticipant
from finances.domain.entities.transaction_type import TransactionType
from finances.domain.entities.expense_category import ExpenseCategory
from finances.domain.value_objects.money import Money
from finances.application.interfaces import TransactionRepository


class ListTransactionsTests(SimpleTestCase):
    def setUp(self):
        self.trans_repo = MagicMock(spec=TransactionRepository)
        
        # Patch registry to avoid DB hits during handler init
        self.registry_patcher = patch("finances.application.use_cases.queries.list_transactions.get_repository_registry")
        self.mock_registry = self.registry_patcher.start()
        
        self.handler = ListTransactionsQueryHandler(transaction_repository=self.trans_repo)
        self.user_id = 1

    def tearDown(self):
        self.registry_patcher.stop()

    def test_list_transactions_delegates_to_repo(self):
        query = ListTransactionsQuery(user_id=self.user_id)
        mock_transaction = Transaction.from_persistence(
            id=uuid4(),
            sender=TransactionParticipant(wallet_id=uuid4(), money=Money(Decimal("10.00"), "USD")),
            receiver=None,
            description="Test",
            type=TransactionType.EXPENSE,
            category=ExpenseCategory.FOOD,
            created_at=datetime.now(timezone.utc)
        )
        self.trans_repo.get_user_transactions.return_value = [mock_transaction]
        
        result = self.handler.handle(query)
        
        self.assertEqual(len(result), 1)
        self.assertIsInstance(result[0], TransactionPlainDTO)
        self.trans_repo.get_user_transactions.assert_called_once_with(self.user_id)
