from data_read_core.shared.logging import get_query_logger


def log_served_from_store(user_id: int, served_count: int, total: int) -> None:
    get_query_logger("list_categories").info(
        "Served %d of %d categories for user %s from read store.",
        served_count,
        total,
        user_id,
    )


def log_served_from_cache(user_id: int) -> None:
    get_query_logger("list_categories").info(
        "Served category list for user %s from cache.",
        user_id,
    )
