from data_read_core.shared.logging import get_query_logger


def log_served_from_store(notification_id: str) -> None:
    logger = get_query_logger()
    logger.info("Served notification %s from read store.", notification_id)


def log_served_from_cache(notification_id: str) -> None:
    logger = get_query_logger()
    logger.info("Served notification %s from cache.", notification_id)
