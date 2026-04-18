from unittest.mock import patch, MagicMock
from uuid import uuid4
from decimal import Decimal
from datetime import datetime, timezone
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from finances.application.dtos import (
    TransactionDTO, 
    TransactionPlainDTO, 
    TransactionParticipantPlainDTO,
    TransactionParticipantDTO,
    WalletDTO
)
from finances.domain.entities import TransactionType, ExpenseCategory
from finances.domain.value_objects.money import Money

User = get_user_model()

class TransactionEndpointTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", email="test@example.com")
        self.client.force_authenticate(user=self.user)
        self.transaction_id = uuid4()
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
        
        participant_plain = TransactionParticipantPlainDTO(
            wallet_id=self.wallet_id,
            currency_code="USD",
            amount=Decimal("10.00")
        )
        
        self.transaction_plain_dto = TransactionPlainDTO(
            id=self.transaction_id,
            sender=participant_plain,
            receiver=None,
            description="Test Transaction",
            type=TransactionType.EXPENSE,
            category=ExpenseCategory.FOOD,
            created_at=datetime.now(timezone.utc)
        )
        
        self.transaction_dto = TransactionDTO(
            id=self.transaction_id,
            sender=TransactionParticipantDTO(
                wallet=self.wallet_dto,
                currency_code="USD",
                amount=Decimal("10.00")
            ),
            receiver=None,
            description="Test Transaction",
            type=TransactionType.EXPENSE,
            category=ExpenseCategory.FOOD,
            created_at=datetime.now(timezone.utc)
        )

    @patch("finances.presentation.http.views.transaction_viewset.ListTransactionsQueryHandler.handle")
    def test_list_transactions(self, mock_handle):
        mock_handle.return_value = [self.transaction_plain_dto]
        
        response = self.client.get("/api/v1/transactions/")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("data", response.data)

    @patch("finances.presentation.http.views.transaction_viewset.GetTransactionQueryHandler.handle")
    def test_retrieve_transaction(self, mock_handle):
        mock_handle.return_value = self.transaction_dto
        
        response = self.client.get(f"/api/v1/transactions/{self.transaction_id}/")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch("finances.presentation.http.views.transaction_viewset.CreateTransactionCommandHandler.handle")
    def test_create_transaction(self, mock_handle):
        mock_handle.return_value = self.transaction_dto
        
        data = {
            "description": "New Trans",
            "type": "EXPENSE",
            "category": "FOOD",
            "sender": {"wallet_id": str(self.wallet_id), "amount": "10.00"}
        }
        response = self.client.post("/api/v1/transactions/", data, format="json")
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @patch("finances.presentation.http.views.transaction_viewset.DeleteTransactionCommandHandler.handle")
    def test_delete_transaction(self, mock_handle):
        # Result of delete is used for message, id is enough
        mock_handle.return_value = self.transaction_dto
        
        response = self.client.delete(f"/api/v1/transactions/{self.transaction_id}/")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch("finances.presentation.http.views.transaction_viewset.ListFilteredTransactionsQueryHandler.handle")
    def test_search_transactions(self, mock_handle):
        mock_handle.return_value = [self.transaction_plain_dto]
        
        data = {"filter_body": {"description": {"contains": "Food"}}}
        response = self.client.post("/api/v1/transactions/search/", data, format="json")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("data", response.data)
