from ..dtos import NotificationDTO


def present_one(notification: NotificationDTO) -> dict:
    return {
        "id": notification.id,
        "severity": notification.severity,
        "title": notification.title,
        "body": notification.body,
        "subject": _present_subject(notification),
        "acknowledged_at": notification.acknowledged_at,
        "created_at": notification.created_at,
        "updated_at": notification.updated_at,
        "deleted_at": notification.deleted_at,
    }


def _present_subject(notification: NotificationDTO) -> dict | None:
    if not notification.subject_type or not notification.subject_id:
        return None

    return {
        "type": notification.subject_type,
        "id": notification.subject_id,
    }
