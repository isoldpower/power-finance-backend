from logging import getLogger

logger = getLogger("query_slices.get_wallet")


def log_served_from_store(wallet_id: str) -> None:
    logger.info("Served wallet %s from read store.", wallet_id)


def log_served_from_cache(wallet_id: str) -> None:
    logger.info("Served wallet %s from cache.", wallet_id)
