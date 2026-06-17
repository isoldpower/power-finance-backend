from data_read_core.shared.logging import get_query_logger


def log_served_from_store(webhook_id: str, count: int) -> None:
    logger = get_query_logger("list_webhook_events")
    logger.info(
        "Served %d subscriptions of webhook %s from read store.",
        count,
        webhook_id,
    )


def log_served_from_cache(webhook_id: str) -> None:
    logger = get_query_logger("list_webhook_events")
    logger.info(
        "Served subscriptions of webhook %s from cache.",
        webhook_id,
    )
