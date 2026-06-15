from data_read_core.shared.logging import get_query_logger


def log_search_served(user_id: int, returned: int, total: int) -> None:
    logger = get_query_logger("search_webhooks")
    logger.info(
        "Served %d of %d webhook search hits for user %s from read store.",
        returned,
        total,
        user_id,
    )
