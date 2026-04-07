from unittest.mock import MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone
from decimal import Decimal
from django.test import SimpleTestCase
from finances.application.use_cases.queries.list_filtered_transactions import ListFilteredTransactionsQuery, ListFilteredTransactionsQueryHandler
from finances.application.dtos import TransactionPlainDTO
from finances.domain.entities.transaction import Transaction, TransactionParticipant
from finances.domain.entities.transaction_type import TransactionType
from finances.domain.entities.expense_category import ExpenseCategory
from finances.domain.value_objects.money import Money
from finances.application.interfaces import TransactionRepository


class ListFilteredTransactionsTests(SimpleTestCase):
    def setUp(self):
        self.trans_repo = MagicMock(spec=TransactionRepository)
        
        # Patch registry to avoid DB hits during handler init
        self.registry_patcher = patch("finances.application.use_cases.queries.list_filtered_transactions.get_repository_registry")
        self.mock_registry = self.registry_patcher.start()
        
        self.handler = ListFilteredTransactionsQueryHandler(transaction_repository=self.trans_repo)
        self.user_id = 1

    def tearDown(self):
        self.registry_patcher.stop()

    def test_list_filtered_transactions_resolves_filter_and_calls_repo(self):
        filter_body = {"field_name": "description", "operator": "contains", "value": "Food"}
        query = ListFilteredTransactionsQuery(user_id=self.user_id, filter_body=filter_body)
        
        mock_transaction = Transaction.from_persistence(
            id=uuid4(),
            sender=TransactionParticipant(wallet_id=uuid4(), money=Money(Decimal("10.00"), "USD")),
            receiver=None,
            description="Food Delivery",
            type=TransactionType.EXPENSE,
            category=ExpenseCategory.FOOD,
            created_at=datetime.now(timezone.utc)
        )
        self.trans_repo.list_transactions_with_filters.return_value = [mock_transaction]
        
        result = self.handler.handle(query)
        
        self.assertEqual(len(result), 1)
        self.assertIsInstance(result[0], TransactionPlainDTO)
        self.assertEqual(result[0].description, "Food Delivery")
        
        self.trans_repo.list_transactions_with_filters.assert_called_once()
        args, kwargs = self.trans_repo.list_transactions_with_filters.call_args
        self.assertEqual(args[1], self.user_id)
