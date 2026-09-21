from data_read_core.shared.logging import get_query_logger


def log_served_from_store(user_id: int, sections: str) -> None:
    logger = get_query_logger("get_metrics")
    logger.info(
        "Built metrics [%s] for user %s from read store.",
        sections,
        user_id,
    )


def log_served_from_cache(user_id: int, sections: str) -> None:
    logger = get_query_logger("get_metrics")
    logger.info(
        "Served metrics [%s] for user %s from cache.",
        sections,
        user_id,
    )
