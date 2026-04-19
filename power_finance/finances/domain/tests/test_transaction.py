from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4
from django.test import SimpleTestCase
from finances.domain.entities.old_transaction import Transaction, TransactionParticipant
from finances.domain.entities.transaction_type import TransactionType
from finances.domain.entities.expense_category import ExpenseCategory
from finances.domain.value_objects.money import Money
from finances.domain.events import EventCollector, TransactionCreatedEvent, TransactionUpdatedEvent, TransactionDeletedEvent


class TransactionTests(SimpleTestCase):
    def setUp(self):
        self.wallet_id_1 = uuid4()
        self.wallet_id_2 = uuid4()
        self.money = Money(amount=Decimal("100.00"), currency_code="USD")
        self.participant_1 = TransactionParticipant(wallet_id=self.wallet_id_1, money=self.money)
        self.participant_2 = TransactionParticipant(wallet_id=self.wallet_id_2, money=self.money)

    def test_create_expense_without_sender_raises_error(self):
        with self.assertRaisesMessage(ValueError, "EXPENSE Transactions must have a sender specified."):
            Transaction.create(
                sender=None,
                receiver=self.participant_2,
                description="Test Expense",
                type=TransactionType.EXPENSE,
                category=ExpenseCategory.FOOD
            )

    def test_create_income_without_receiver_raises_error(self):
        with self.assertRaisesMessage(ValueError, "INCOME Transactions must have a receiver specified."):
            Transaction.create(
                sender=self.participant_1,
                receiver=None,
                description="Test Income",
                type=TransactionType.INCOME,
                category=ExpenseCategory.FOOD
            )

    def test_create_transfer_without_both_parties_raises_error(self):
        with self.assertRaisesMessage(ValueError, "Transaction with type set to TRANSFER should have both sender and receiver specified."):
            Transaction.create(
                sender=self.participant_1,
                receiver=None,
                description="Test Transfer",
                type=TransactionType.TRANSFER,
                category=ExpenseCategory.FOOD
            )

    def test_create_valid_income_emits_event(self):
        event_collector = EventCollector()
        transaction = Transaction.create(
            sender=None,
            receiver=self.participant_2,
            description="Valid Income",
            type=TransactionType.INCOME,
            category=ExpenseCategory.FOOD,
            event_collector=event_collector
        )
        
        events = event_collector.pull_events()
        self.assertEqual(len(events), 1)
        self.assertIsInstance(events[0], TransactionCreatedEvent)
        self.assertEqual(events[0].transaction_id, transaction.id)

    def test_create_valid_expense_emits_event(self):
        event_collector = EventCollector()
        transaction = Transaction.create(
            sender=self.participant_1,
            receiver=None,
            description="Valid Expense",
            type=TransactionType.EXPENSE,
            category=ExpenseCategory.FOOD,
            event_collector=event_collector
        )
        
        events = event_collector.pull_events()
        self.assertEqual(len(events), 1)
        self.assertIsInstance(events[0], TransactionCreatedEvent)
        self.assertEqual(events[0].transaction_id, transaction.id)

    def test_from_persistence_valid_round_trip(self):
        transaction_id = uuid4()
        created_at = datetime.now(timezone.utc)
        transaction = Transaction.from_persistence(
            id=transaction_id,
            sender=self.participant_1,
            receiver=self.participant_2,
            description="From Persistence",
            type=TransactionType.TRANSFER,
            category=ExpenseCategory.FOOD,
            created_at=created_at
        )
        
        self.assertEqual(transaction.id, transaction_id)
        self.assertEqual(transaction.description, "From Persistence")
        self.assertEqual(transaction.created_at, created_at)

    def test_update_fields_emits_event(self):
        transaction = Transaction.from_persistence(
            id=uuid4(),
            sender=self.participant_1,
            receiver=None,
            description="Original",
            type=TransactionType.EXPENSE,
            category=ExpenseCategory.FOOD,
            created_at=datetime.now(timezone.utc)
        )
        
        transaction.update_fields(category=ExpenseCategory.ENTERTAINMENT)
        
        events = transaction._event_collector.pull_events()
        self.assertEqual(len(events), 1)
        self.assertIsInstance(events[0], TransactionUpdatedEvent)
        self.assertEqual(transaction.category, ExpenseCategory.ENTERTAINMENT)

    def test_update_fields_no_op_emits_no_event(self):
        transaction = Transaction.from_persistence(
            id=uuid4(),
            sender=self.participant_1,
            receiver=None,
            description="Original",
            type=TransactionType.EXPENSE,
            category=ExpenseCategory.FOOD,
            created_at=datetime.now(timezone.utc)
        )
        
        transaction.update_fields(description="Original")
        
        events = transaction._event_collector.pull_events()
        self.assertEqual(len(events), 0)

    def test_confirm_delete_emits_event(self):
        transaction = Transaction.from_persistence(
            id=uuid4(),
            sender=self.participant_1,
            receiver=None,
            description="To Delete",
            type=TransactionType.EXPENSE,
            category=ExpenseCategory.FOOD,
            created_at=datetime.now(timezone.utc)
        )
        
        transaction.confirm_delete()
        
        events = transaction._event_collector.pull_events()
        self.assertEqual(len(events), 1)
        self.assertIsInstance(events[0], TransactionDeletedEvent)

    def test_migrate_event_collector(self):
        transaction = Transaction.from_persistence(
            id=uuid4(),
            sender=self.participant_1,
            receiver=None,
            description="Migrate",
            type=TransactionType.EXPENSE,
            category=ExpenseCategory.FOOD,
            created_at=datetime.now(timezone.utc)
        )
        
        transaction.confirm_delete()
        
        new_collector = EventCollector()
        transaction.migrate_event_collector(new_collector)
        
        self.assertEqual(len(new_collector.pull_events()), 1)
        self.assertIs(transaction._event_collector, new_collector)
