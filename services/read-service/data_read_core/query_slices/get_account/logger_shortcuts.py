from data_read_core.shared.logging import get_query_logger


def log_served_from_store(account_id: str) -> None:
    logger = get_query_logger("get_account")
    logger.info("Served account %s from read store.", account_id)


def log_served_from_cache(account_id: str) -> None:
    logger = get_query_logger("get_account")
    logger.info("Served account %s from cache.", account_id)
