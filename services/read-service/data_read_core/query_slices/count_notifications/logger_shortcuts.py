from data_read_core.shared.logging import get_query_logger


def log_counts_served(user_id: int, unacknowledged: int, total: int) -> None:
    logger = get_query_logger("count_notifications")
    logger.info(
        "Served notification counts for user %s (%d unacknowledged of %d).",
        user_id,
        unacknowledged,
        total,
    )
