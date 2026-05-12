from decimal import Decimal
from unittest.mock import MagicMock, patch
from django.test import TestCase
from finances.application.use_cases.commands.create_new_wallet import CreateNewWalletCommand, CreateNewWalletCommandHandler
from finances.application.dtos import WalletDTO
from finances.domain.entities.wallet import Wallet
from finances.domain.value_objects.money import Money
from finances.domain.exceptions.money import UnsupportedCurrencyError
from finances.application.interfaces import WalletRepository, CurrencyRepository


class CreateNewWalletTests(TestCase):
    def setUp(self):
        self.wallet_repo = MagicMock(spec=WalletRepository)
        self.currency_repo = MagicMock(spec=CurrencyRepository)
        
        # Patch registry to avoid DB hits during handler init
        self.registry_patcher = patch("finances.application.use_cases.commands.create_new_wallet.get_repository_registry")
        self.mock_registry = self.registry_patcher.start()
        
        # Patch transaction.atomic
        self.atomic_patcher = patch("django.db.transaction.atomic")
        self.mock_atomic = self.atomic_patcher.start()
        self.mock_atomic.return_value.__enter__.return_value = None

        self.handler = CreateNewWalletCommandHandler(
            wallet_repository=self.wallet_repo,
            currency_repository=self.currency_repo
        )

    def tearDown(self):
        self.registry_patcher.stop()
        self.atomic_patcher.stop()

    def test_currency_not_found_raises_error(self):
        command = CreateNewWalletCommand(
            user_id=1,
            name="New Wallet",
            balance_amount=Decimal("100.00"),
            currency="INVALID",
            credit=False
        )
        self.currency_repo.currency_code_exists.return_value = False
        
        with self.assertRaises(UnsupportedCurrencyError):
            self.handler.handle(command)

    def test_valid_command_creates_wallet(self):
        command = CreateNewWalletCommand(
            user_id=1,
            name="New Wallet",
            balance_amount=Decimal("100.00"),
            currency="USD",
            credit=False
        )
        self.currency_repo.currency_code_exists.return_value = True
        
        # Mock create_wallet to return the wallet it received
        self.wallet_repo.create_wallet.side_effect = lambda w: w
        
        result = self.handler.handle(command)
        
        self.assertIsInstance(result, WalletDTO)
        self.assertEqual(result.name, "New Wallet")
        self.assertEqual(result.balance_amount, Decimal("100.00"))
        self.wallet_repo.create_wallet.assert_called_once()
