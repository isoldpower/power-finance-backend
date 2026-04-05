from decimal import Decimal
from unittest.mock import MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone
from django.test import TestCase
from finances.application.use_cases.commands.create_transaction import CreateTransactionCommand, CreateTransactionCommandHandler
from finances.application.dtos import CreateTransactionParticipantDTO, TransactionDTO
from finances.domain.entities.transaction import Transaction
from finances.domain.entities.transaction_type import TransactionType
from finances.domain.entities.expense_category import ExpenseCategory
from finances.domain.entities.wallet import Wallet
from finances.domain.value_objects.money import Money
from finances.application.interfaces import TransactionRepository, WalletRepository


class CreateTransactionTests(TestCase):
    def setUp(self):
        self.trans_repo = MagicMock(spec=TransactionRepository)
        self.wallet_repo = MagicMock(spec=WalletRepository)
        
        # Patch registry to avoid DB hits during handler init
        self.registry_patcher = patch("finances.application.use_cases.commands.create_transaction.get_repository_registry")
        self.mock_registry = self.registry_patcher.start()
        
        # Patch transaction methods
        self.atomic_patcher = patch("django.db.transaction.atomic")
        self.on_commit_patcher = patch("django.db.transaction.on_commit")
        self.mock_atomic = self.atomic_patcher.start()
        self.mock_on_commit = self.on_commit_patcher.start()
        self.mock_atomic.return_value.__enter__.return_value = None

        self.handler = CreateTransactionCommandHandler(
            transaction_repository=self.trans_repo,
            wallet_repository=self.wallet_repo
        )
        self.user_id = 1
        self.wallet_id_receiver = uuid4()
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

    def tearDown(self):
        self.registry_patcher.stop()
        self.atomic_patcher.stop()
        self.on_commit_patcher.stop()

    def test_valid_income_creates_transaction_and_saves_wallet(self):
        command = CreateTransactionCommand(
            user_id=self.user_id,
            sender=None,
            receiver=CreateTransactionParticipantDTO(wallet_id=self.wallet_id_receiver, amount=Decimal("30.00")),
            description="Salary",
            type=TransactionType.INCOME,
            category=ExpenseCategory.FOOD
        )
        
        self.wallet_repo.get_user_wallet_for_update.return_value = self.receiver_wallet
        self.trans_repo.create_transaction.side_effect = lambda t: t
        
        result = self.handler.handle(command)
        
        self.assertIsInstance(result, TransactionDTO)
        self.assertEqual(result.receiver.wallet.id, self.wallet_id_receiver)
        self.assertEqual(self.receiver_wallet.balance.amount, Decimal("80.00"))
        
        self.wallet_repo.save_wallet.assert_called_once_with(self.receiver_wallet)
        self.trans_repo.create_transaction.assert_called_once()

    def test_sender_wallet_not_found_creates_transaction_without_sender(self):
        from django.core.exceptions import ObjectDoesNotExist
        
        command = CreateTransactionCommand(
            user_id=self.user_id,
            sender=CreateTransactionParticipantDTO(wallet_id=uuid4(), amount=Decimal("20.00")),
            receiver=CreateTransactionParticipantDTO(wallet_id=self.wallet_id_receiver, amount=Decimal("20.00")),
            description="Transfer",
            type=TransactionType.TRANSFER,
            category=ExpenseCategory.FOOD
        )
        
        self.wallet_repo.get_user_wallet_for_update.side_effect = [ObjectDoesNotExist(), self.receiver_wallet]
        
        with self.assertRaises(ValueError):
            self.handler.handle(command)
