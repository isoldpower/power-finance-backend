from data_read_core.shared.logging import get_query_logger


def log_served_from_store(webhook_id: str) -> None:
    logger = get_query_logger()
    logger.info("Served webhook %s from read store.", webhook_id)


def log_served_from_cache(webhook_id: str) -> None:
    logger = get_query_logger()
    logger.info("Served webhook %s from cache.", webhook_id)
