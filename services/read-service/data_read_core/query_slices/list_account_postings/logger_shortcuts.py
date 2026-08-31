from data_read_core.shared.logging import get_query_logger

from .dtos import AccountPostingDTO


def log_served_from_store(account_id: str, postings: list[AccountPostingDTO], total: int):
    logger = get_query_logger("list_account_postings")
    logger.info(
        "Served %d of %d postings for account %s from read store.",
        len(postings),
        total,
        account_id,
    )


def log_served_from_cache(account_id: str):
    logger = get_query_logger("list_account_postings")
    logger.info("Served posting list for account %s from cache.", account_id)
