from data_read_core.shared.logging import get_query_logger

from .dtos import AccountDTO


def log_served_from_store(user_id: int, accounts: list[AccountDTO], total: int):
    logger = get_query_logger("list_accounts")
    logger.info(
        "Served %d of %d accounts for user %s from read store.",
        len(accounts),
        total,
        user_id,
    )


def log_served_from_cache(user_id: int):
    logger = get_query_logger("list_accounts")
    logger.info("Served account list for user %s from cache.", user_id)
