from unittest.mock import patch, MagicMock
from uuid import uuid4
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from finances.domain.entities import Notification

User = get_user_model()

class NotificationEndpointTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", email="test@example.com")
        self.client.force_authenticate(user=self.user)
        self.notification_id = uuid4()

    @patch("finances.presentation.http.views.notification_views.ListNotificationsQueryHandler.handle")
    def test_list_notifications(self, mock_handle):
        mock_handle.return_value = []
        
        response = self.client.get("/api/v1/notifications/")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("data", response.data)

    @patch("finances.presentation.http.views.notification_views.AcknowledgeNotificationCommandHandler.handle")
    def test_acknowledge_notification(self, mock_handle):
        mock_notification = MagicMock(spec=Notification)
        mock_notification.id = self.notification_id
        mock_handle.return_value = mock_notification
        
        response = self.client.post(f"/api/v1/notifications/{self.notification_id}/ack/")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch("finances.presentation.http.views.notification_views.AcknowledgeNotificationCommandHandler.handle")
    def test_acknowledge_notification_permission_denied(self, mock_handle):
        mock_handle.side_effect = PermissionError("Denied")
        
        response = self.client.post(f"/api/v1/notifications/{self.notification_id}/ack/")
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch("finances.presentation.http.views.notification_views.AcknowledgeNotificationCommandHandler.handle")
    def test_acknowledge_notification_not_found(self, mock_handle):
        mock_handle.side_effect = ValueError("Not found")
        
        response = self.client.post(f"/api/v1/notifications/{self.notification_id}/ack/")
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch("finances.presentation.http.views.notification_views.BatchAcknowledgeNotificationCommandHandler.handle")
    def test_batch_acknowledge_notifications(self, mock_handle):
        mock_handle.return_value = [str(self.notification_id)]
        
        data = {"batch": [str(self.notification_id)]}
        response = self.client.post("/api/v1/notifications/ack/", data, format="json")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_unauthenticated_request_fails(self):
        self.client.force_authenticate(user=None)
        response = self.client.get("/api/v1/notifications/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
