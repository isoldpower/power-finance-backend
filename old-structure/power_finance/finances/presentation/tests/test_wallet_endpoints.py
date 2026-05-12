from unittest.mock import patch, MagicMock
from uuid import uuid4
from decimal import Decimal
from datetime import datetime, timezone
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from finances.application.dtos import WalletDTO
from finances.domain.value_objects.money import Money

User = get_user_model()

class WalletEndpointTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", email="test@example.com")
        self.client.force_authenticate(user=self.user)
        self.wallet_id = uuid4()
        self.wallet_dto = WalletDTO(
            id=self.wallet_id,
            user_id=self.user.id,
            name="Test Wallet",
            balance_amount=Decimal("100.00"),
            currency="USD",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )

    @patch("finances.presentation.http.views.wallet_viewset.ListOwnedWalletsQueryHandler.handle")
    def test_list_wallets(self, mock_handle):
        mock_handle.return_value = [self.wallet_dto]
        
        response = self.client.get("/api/v1/wallets/")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Check standard pagination structure
        self.assertIn("data", response.data)
        self.assertEqual(len(response.data["data"]), 1)
        self.assertEqual(response.data["data"][0]["name"], "Test Wallet")

    @patch("finances.presentation.http.views.wallet_viewset.GetOwnedWalletQueryHandler.handle")
    def test_retrieve_wallet(self, mock_handle):
        mock_handle.return_value = self.wallet_dto
        
        response = self.client.get(f"/api/v1/wallets/{self.wallet_id}/")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Test Wallet")

    @patch("finances.presentation.http.views.wallet_viewset.CreateNewWalletCommandHandler.handle")
    def test_create_wallet(self, mock_handle):
        mock_handle.return_value = self.wallet_dto
        
        data = {
            "name": "New Wallet",
            "balance": {"amount": "100.00", "currency": "USD"},
            "credit": False
        }
        response = self.client.post("/api/v1/wallets/", data, format="json")
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], "Test Wallet")

    @patch("finances.presentation.http.views.wallet_viewset.UpdateExistingWalletCommandHandler.handle")
    def test_update_wallet(self, mock_handle):
        mock_handle.return_value = self.wallet_dto
        
        data = {
            "name": "Updated Wallet",
            "balance_amount": "150.00",
            "currency": "USD",
            "credit": True
        }
        response = self.client.patch(f"/api/v1/wallets/{self.wallet_id}/", data, format="json")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch("finances.presentation.http.views.wallet_viewset.SoftDeleteWalletCommandHandler.handle")
    def test_delete_wallet(self, mock_handle):
        mock_handle.return_value = self.wallet_dto
        
        response = self.client.delete(f"/api/v1/wallets/{self.wallet_id}/")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch("finances.presentation.http.views.wallet_viewset.ListFilteredWalletsQueryHandler.handle")
    def test_search_wallets(self, mock_handle):
        mock_handle.return_value = [self.wallet_dto]
        
        data = {"filter_body": {"name": {"contains": "Test"}}}
        response = self.client.post("/api/v1/wallets/search/", data, format="json")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("data", response.data)
