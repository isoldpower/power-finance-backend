from unittest.mock import MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone
from decimal import Decimal
from django.test import SimpleTestCase
from finances.application.use_cases.queries.list_filtered_wallets import ListFilteredWalletsQuery, ListFilteredWalletsQueryHandler
from finances.application.dtos import WalletDTO
from finances.domain.entities.wallet import Wallet
from finances.domain.value_objects.money import Money
from finances.application.interfaces import WalletRepository


class ListFilteredWalletsTests(SimpleTestCase):
    def setUp(self):
        self.wallet_repo = MagicMock(spec=WalletRepository)
        
        # Patch registry to avoid DB hits during handler init
        self.registry_patcher = patch("finances.application.use_cases.queries.list_filtered_wallets.get_repository_registry")
        self.mock_registry = self.registry_patcher.start()
        
        self.handler = ListFilteredWalletsQueryHandler(wallet_repository=self.wallet_repo)
        self.user_id = 1

    def tearDown(self):
        self.registry_patcher.stop()

    def test_list_filtered_wallets_resolves_filter_and_calls_repo(self):
        filter_body = {"field_name": "name", "operator": "contains", "value": "Savings"}
        query = ListFilteredWalletsQuery(user_id=self.user_id, filter_body=filter_body)
        
        mock_wallet = Wallet(
            id=uuid4(),
            user_id=self.user_id,
            name="Savings Wallet",
            balance=Money(Decimal("100.00"), "USD"),
            credit=False,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            deleted_at=None
        )
        self.wallet_repo.list_wallets_with_filters.return_value = [mock_wallet]
        
        result = self.handler.handle(query)
        
        self.assertEqual(len(result), 1)
        self.assertIsInstance(result[0], WalletDTO)
        self.assertEqual(result[0].name, "Savings Wallet")
        
        # Verify repo was called with some ResolvedFilterTree
        self.wallet_repo.list_wallets_with_filters.assert_called_once()
        args, kwargs = self.wallet_repo.list_wallets_with_filters.call_args
        self.assertEqual(args[1], self.user_id)
