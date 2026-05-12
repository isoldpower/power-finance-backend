from unittest.mock import MagicMock, patch
from uuid import uuid4
from django.test import SimpleTestCase
from django.core.exceptions import ObjectDoesNotExist
from finances.application.use_cases.commands.acknowledge_notification import (
    AcknowledgeNotificationCommand,
    AcknowledgeNotificationCommandHandler,
    BatchAcknowledgeNotificationCommand,
    BatchAcknowledgeNotificationCommandHandler
)
from finances.domain.entities import Notification
from finances.application.interfaces import NotificationRepository


class AcknowledgeNotificationTests(SimpleTestCase):
    def setUp(self):
        self.notification_repo = MagicMock(spec=NotificationRepository)
        
        # Patch registry to avoid DB hits during handler init
        self.registry_patcher = patch("finances.application.use_cases.commands.acknowledge_notification.get_repository_registry")
        self.mock_registry = self.registry_patcher.start()

        self.handler = AcknowledgeNotificationCommandHandler(notification_repository=self.notification_repo)
        self.batch_handler = BatchAcknowledgeNotificationCommandHandler(notification_repository=self.notification_repo)
        self.user_id = 1
        self.notification_id = uuid4()

    def tearDown(self):
        self.registry_patcher.stop()

    def test_single_ack_happy_path(self):
        command = AcknowledgeNotificationCommand(user_id=self.user_id, notification_id=self.notification_id)
        mock_notification = MagicMock(spec=Notification)
        mock_notification.user_id = self.user_id
        
        self.notification_repo.get_notification_by_id.return_value = mock_notification
        self.notification_repo.mark_notification_delivered.return_value = mock_notification
        
        result = self.handler.handle(command)
        
        self.assertEqual(result, mock_notification)
        self.notification_repo.mark_notification_delivered.assert_called_once_with(self.notification_id)

    def test_ack_notification_of_another_user_raises_permission_error(self):
        command = AcknowledgeNotificationCommand(user_id=self.user_id, notification_id=self.notification_id)
        mock_notification = MagicMock(spec=Notification)
        mock_notification.user_id = 2 # Different user
        
        self.notification_repo.get_notification_by_id.return_value = mock_notification
        
        with self.assertRaises(PermissionError):
            self.handler.handle(command)

    def test_ack_non_existent_notification_raises_value_error(self):
        command = AcknowledgeNotificationCommand(user_id=self.user_id, notification_id=self.notification_id)
        self.notification_repo.get_notification_by_id.side_effect = ObjectDoesNotExist()
        
        with self.assertRaises(ValueError):
            self.handler.handle(command)

    def test_batch_ack_happy_path(self):
        ids = [uuid4(), uuid4()]
        command = BatchAcknowledgeNotificationCommand(user_id=self.user_id, notification_ids=ids)
        
        mock_notifications = [MagicMock(spec=Notification, id=ids[0]), MagicMock(spec=Notification, id=ids[1])]
        self.notification_repo.mark_notifications_delivered.return_value = mock_notifications
        
        result = self.batch_handler.handle(command)
        
        self.assertEqual(result, [str(ids[0]), str(ids[1])])
        self.notification_repo.mark_notifications_delivered.assert_called_once_with(ids, self.user_id)
