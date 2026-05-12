from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
from uuid import uuid4
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from finances.application.dtos import WebhookDTO, WebhookSubscriptionDTO

User = get_user_model()

class WebhookEndpointTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", email="test@example.com")
        self.client.force_authenticate(user=self.user)
        self.webhook_id = uuid4()
        
        # Real DTO for webhook
        self.webhook_dto = WebhookDTO(
            id=self.webhook_id,
            title="Test Webhook",
            url="https://example.com/webhook",
            secret="test-secret",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        # Real DTO for subscription
        self.subscription_id = uuid4()
        self.sub_dto = WebhookSubscriptionDTO(
            id=self.subscription_id,
            endpoint_id=self.webhook_id,
            event_type="transaction.created",
            is_active=True
        )
        
        # Patch all handlers used in WebhooksViewSet
        self.patchers = [
            patch("finances.presentation.http.views.webhooks_viewset.ListWebhooksQueryHandler"),
            patch("finances.presentation.http.views.webhooks_viewset.GetWebhookQueryHandler"),
            patch("finances.presentation.http.views.webhooks_viewset.CreateWebhookEndpointCommandHandler"),
            patch("finances.presentation.http.views.webhooks_viewset.RotateWebhookSecretCommandHandler"),
            patch("finances.presentation.http.views.webhooks_viewset.GetWebhookSubscriptionsQueryHandler"),
            patch("finances.presentation.http.views.webhooks_viewset.SubscribeToEventCommandHandler"),
        ]
        self.mocks = [p.start() for p in self.patchers]

    def tearDown(self):
        for p in self.patchers:
            p.stop()

    def test_list_webhooks(self):
        # self.mocks[0] is ListWebhooksQueryHandler
        self.mocks[0].return_value.handle.return_value = [self.webhook_dto]
        
        response = self.client.get("/api/v1/webhooks/")
        
        self.assertEqual(response.status_code, status.HTTP_206_PARTIAL_CONTENT)
        self.assertIn("data", response.data)

    def test_retrieve_webhook(self):
        # self.mocks[1] is GetWebhookQueryHandler
        self.mocks[1].return_value.handle.return_value = self.webhook_dto
        
        response = self.client.get(f"/api/v1/webhooks/{self.webhook_id}/")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_webhook(self):
        # self.mocks[2] is CreateWebhookEndpointCommandHandler
        self.mocks[2].return_value.handle.return_value = self.webhook_dto
        
        data = {"title": "New Webhook", "url": "https://example.com/new"}
        response = self.client.post("/api/v1/webhooks/", data, format="json")
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_rotate_secret(self):
        # self.mocks[3] is RotateWebhookSecretCommandHandler
        self.mocks[3].return_value.handle.return_value = self.webhook_dto
        
        response = self.client.post(f"/api/v1/webhooks/{self.webhook_id}/rotate/")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_events(self):
        # self.mocks[4] is GetWebhookSubscriptionsQueryHandler
        self.mocks[4].return_value.handle.return_value = [self.sub_dto]
        
        response = self.client.get(f"/api/v1/webhooks/{self.webhook_id}/events/")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_subscribe_to_event(self):
        # self.mocks[5] is SubscribeToEventCommandHandler
        self.mocks[5].return_value.handle.return_value = self.sub_dto
        
        data = {"event_type": "transaction.created"}
        response = self.client.post(f"/api/v1/webhooks/{self.webhook_id}/events/", data, format="json")
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
