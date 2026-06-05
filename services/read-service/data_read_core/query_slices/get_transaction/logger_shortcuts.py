from logging import getLogger

logger = getLogger("query_slices.get_transaction")


def log_served_from_store(transaction_id: str) -> None:
    logger.info("Served transaction %s from read store.", transaction_id)


def log_served_from_cache(transaction_id: str) -> None:
    logger.info("Served transaction %s from cache.", transaction_id)
