from data_read_core.shared.logging import get_query_logger


def log_served_from_store(report_name: str, user_id: int) -> None:
    logger = get_query_logger(report_name)
    logger.info("Built analytics %s for user %s from read store.", report_name, user_id)


def log_served_from_cache(report_name: str, user_id: int) -> None:
    logger = get_query_logger(report_name)
    logger.info("Served analytics %s for user %s from cache.", report_name, user_id)
