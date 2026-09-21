from data_read_core.shared.logging import get_query_logger


def log_rates_served(base_code: str, count: int) -> None:
    logger = get_query_logger("get_currency_rates")
    logger.info("Served %d rates against %s.", count, base_code)
