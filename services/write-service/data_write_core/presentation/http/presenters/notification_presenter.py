from write_service.common.timestamps import to_iso

from data_write_core.application.dtos import NotificationDTO


class NotificationHttpPresenter:
    @staticmethod
    def present_one(notification: NotificationDTO) -> dict:
        return {
            "id": str(notification.id),
            "severity": notification.severity,
            "title": notification.title,
            "body": notification.body,
            "subject": NotificationHttpPresenter._present_subject(notification),
            "acknowledged_at": to_iso(notification.acknowledged_at),
            "created_at": to_iso(notification.created_at),
            "updated_at": to_iso(notification.updated_at),
            "deleted_at": to_iso(notification.deleted_at),
        }

    @staticmethod
    def present_many(notifications: list[NotificationDTO]) -> list[dict]:
        return [
            NotificationHttpPresenter.present_one(notification) for notification in notifications
        ]

    @staticmethod
    def _present_subject(notification: NotificationDTO) -> dict | None:
        if not notification.subject_type or not notification.subject_id:
            return None

        return {
            "type": notification.subject_type,
            "id": notification.subject_id,
        }
