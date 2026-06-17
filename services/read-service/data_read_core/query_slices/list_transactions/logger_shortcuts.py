from ...shared.logging import get_query_logger
from .dtos import TransactionDTO


def log_served_from_store(
    user_id: int,
    transactions: list[TransactionDTO],
    total: int,
):
    logger = get_query_logger("list_transactions")
    logger.info(
        "Served %d of %d transactions for user %s from read store.",
        len(transactions),
        total,
        user_id,
    )


def log_served_from_cache(user_id: int):
    logger = get_query_logger("list_transactions")
    logger.info(
        "Served transaction list for user %s from cache.",
        user_id,
    )
