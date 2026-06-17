from data_read_core.shared.logging import get_query_logger

from .dtos import NotificationDTO


def log_served_from_store(
    user_id: int,
    notifications: list[NotificationDTO],
    total: int,
):
    logger = get_query_logger("list_notifications")
    logger.info(
        "Served %d of %d notifications for user %s from read store.",
        len(notifications),
        total,
        user_id,
    )


def log_served_from_cache(user_id: int):
    logger = get_query_logger("list_notifications")
    logger.info(
        "Served notification list for user %s from cache.",
        user_id,
    )
