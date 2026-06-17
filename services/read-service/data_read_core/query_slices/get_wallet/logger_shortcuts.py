from data_read_core.shared.logging import get_query_logger


def log_served_from_store(wallet_id: str) -> None:
    logger = get_query_logger()
    logger.info("Served wallet %s from read store.", wallet_id)


def log_served_from_cache(wallet_id: str) -> None:
    logger = get_query_logger()
    logger.info("Served wallet %s from cache.", wallet_id)
