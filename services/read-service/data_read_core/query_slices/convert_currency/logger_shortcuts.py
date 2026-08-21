from data_read_core.shared.logging import get_query_logger


def log_conversion_served(from_code: str, to_code: str) -> None:
    logger = get_query_logger("convert_currency")
    logger.info("Converted %s to %s.", from_code, to_code)
