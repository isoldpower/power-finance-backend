from data_read_core.shared.logging import get_query_logger


def log_served_from_store(user_id: int, automations: list, total: int) -> None:
    logger = get_query_logger("list_automations")
    logger.info(
        "Served %d of %d automations for user %s from read store.",
        len(automations),
        total,
        user_id,
    )


def log_served_from_cache(user_id: int) -> None:
    logger = get_query_logger("list_automations")
    logger.info("Served automation list for user %s from cache.", user_id)
