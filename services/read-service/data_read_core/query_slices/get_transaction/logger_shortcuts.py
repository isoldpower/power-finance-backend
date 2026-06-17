from data_read_core.shared.logging import get_query_logger


def log_served_from_store(transaction_id: str) -> None:
    logger = get_query_logger()
    logger.info("Served transaction %s from read store.", transaction_id)


def log_served_from_cache(transaction_id: str) -> None:
    logger = get_query_logger()
    logger.info("Served transaction %s from cache.", transaction_id)
