from data_read_core.shared.logging import get_query_logger


def log_served_from_store(goal_id: str) -> None:
    logger = get_query_logger("get_goal")
    logger.info("Served goal %s from read store.", goal_id)


def log_served_from_cache(goal_id: str) -> None:
    logger = get_query_logger("get_goal")
    logger.info("Served goal %s from cache.", goal_id)
