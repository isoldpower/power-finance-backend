from data_read_core.shared.logging import get_query_logger


def log_search_served(user_id: int, returned: int, total: int) -> None:
    logger = get_query_logger("search_transactions")
    logger.info(
        "Served %d of %d transaction search hits for user %s from Elasticsearch.",
        returned,
        total,
        user_id,
    )
