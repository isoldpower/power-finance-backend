from logging import getLogger

from .dtos import WalletDTO

logger = getLogger("query_slices.list_wallets")


def log_served_from_store(
    user_id: int,
    wallets: list[WalletDTO],
    total: int,
):
    logger.info(
        "Served %d of %d wallets for user %s from read store.",
        len(wallets),
        total,
        user_id,
    )


def log_served_from_cache(user_id: int):
    logger.info(
        "Served wallet list for user %s from cache.",
        user_id,
    )
