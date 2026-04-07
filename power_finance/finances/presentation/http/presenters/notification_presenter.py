from finances.domain.entities import Notification
from ..serializers import NotificationResponseSerializer

class NotificationHttpPresenter:
    @staticmethod
    def present_many(notifications: list[Notification]) -> list[dict]:
        return [
            NotificationResponseSerializer({
                'id': notification.id,
                'short': notification.short,
                'message': notification.message,
                'is_read': notification.is_read,
                'payload': notification.payload,
                'created_at': notification.created_at
            }).data
            for notification in notifications
        ]
