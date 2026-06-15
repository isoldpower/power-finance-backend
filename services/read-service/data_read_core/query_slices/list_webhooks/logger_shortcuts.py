from data_read_core.shared.logging import get_query_logger

from .dtos import WebhookDTO


def log_served_from_store(
    user_id: int,
    webhooks: list[WebhookDTO],
    total: int,
):
    logger = get_query_logger("list_webhooks")
    logger.info(
        "Served %d of %d webhooks for user %s from read store.",
        len(webhooks),
        total,
        user_id,
    )


def log_served_from_cache(user_id: int):
    logger = get_query_logger("list_webhooks")
    logger.info(
        "Served webhook list for user %s from cache.",
        user_id,
    )
