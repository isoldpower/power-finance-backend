from data_read_core.shared.logging import get_query_logger


def log_served_from_store(automation_id: str) -> None:
    logger = get_query_logger("get_automation")
    logger.info("Served automation %s from read store.", automation_id)
