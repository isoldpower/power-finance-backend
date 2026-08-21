from write_service.common.timestamps import to_iso

from data_write_core.application.dtos import NotificationDTO


class NotificationHttpPresenter:
    @staticmethod
    def present_one(notification: NotificationDTO) -> dict:
        return {
            "id": str(notification.id),
            "short": notification.short,
            "message": notification.message,
            "payload": notification.payload,
            "is_read": notification.is_read,
            "created_at": to_iso(notification.created_at),
            "updated_at": None,
            "deleted_at": None,
        }

    @staticmethod
    def present_many(notifications: list[NotificationDTO]) -> list[dict]:
        return [
            NotificationHttpPresenter.present_one(notification) for notification in notifications
        ]
