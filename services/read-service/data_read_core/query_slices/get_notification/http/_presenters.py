from ..dtos import NotificationDTO


def present_one(notification: NotificationDTO) -> dict:
    return {
        "id": notification.id,
        "short": notification.short,
        "message": notification.message,
        "payload": notification.payload,
        "is_read": notification.is_read,
        "created_at": notification.created_at,
    }
