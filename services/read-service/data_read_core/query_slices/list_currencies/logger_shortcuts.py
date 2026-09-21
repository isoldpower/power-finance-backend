from data_read_core.shared.logging import get_query_logger


def log_served_from_catalog(count: int) -> None:
    logger = get_query_logger("list_currencies")
    logger.info("Served %d currencies from the reference catalog.", count)
