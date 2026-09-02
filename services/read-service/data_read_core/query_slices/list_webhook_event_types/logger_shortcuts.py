from data_read_core.shared.logging import get_query_logger


def log_served_from_catalog(count: int) -> None:
    logger = get_query_logger("list_webhook_event_types")
    logger.info("Served %d webhook event types from the shared catalog.", count)
