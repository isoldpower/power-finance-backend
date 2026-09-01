from data_read_core.shared.logging import get_query_logger


def log_served_from_store(user_id: int, actions: list, total: int) -> None:
    logger = get_query_logger("list_actions")
    logger.info(
        "Served %d of %d actions for user %s from read store.",
        len(actions),
        total,
        user_id,
    )


def log_served_from_cache(user_id: int) -> None:
    logger = get_query_logger("list_actions")
    logger.info("Served action queue for user %s from cache.", user_id)
