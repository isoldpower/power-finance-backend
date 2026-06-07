from data_read_core.shared.logging import get_query_logger

from .dtos import WalletDTO


def log_served_from_store(
    user_id: int,
    wallets: list[WalletDTO],
    total: int,
):
    logger = get_query_logger("list_wallets")
    logger.info(
        "Served %d of %d wallets for user %s from read store.",
        len(wallets),
        total,
        user_id,
    )


def log_served_from_cache(user_id: int):
    logger = get_query_logger("list_wallets")
    logger.info(
        "Served wallet list for user %s from cache.",
        user_id,
    )
