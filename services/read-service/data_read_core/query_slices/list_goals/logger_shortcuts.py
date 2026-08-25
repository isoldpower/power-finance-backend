from data_read_core.shared.logging import get_query_logger

from .dtos import GoalDTO


def log_served_from_store(
    user_id: int,
    goals: list[GoalDTO],
    total: int,
):
    logger = get_query_logger("list_goals")
    logger.info(
        "Served %d of %d goals for user %s from read store.",
        len(goals),
        total,
        user_id,
    )


def log_served_from_cache(user_id: int):
    logger = get_query_logger("list_goals")
    logger.info(
        "Served goal list for user %s from cache.",
        user_id,
    )
