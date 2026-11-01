from read_at_least_py import NotCaughtUp

from data_read_core.shared.logging import get_main_logger


def log_ral_not_satisfied(
    user_scope: str,
    not_caught_up: NotCaughtUp,
) -> None:
    logger = get_main_logger("read_at_least")
    logger.info(
        "Read-At-Least not satisfied for user %s: applied=%s required=%s.",
        user_scope,
        not_caught_up.applied,
        not_caught_up.required,
    )


def log_recorded_outbox_sequence(outbox_seq: int, user_id: int) -> None:
    logger = get_main_logger("read_at_least")
    logger.debug(
        "Recorded applied outbox seq %s for user %s.",
        outbox_seq,
        user_id,
    )


def log_es_ral_not_satisfied(
    user_scope: str,
    not_caught_up: NotCaughtUp,
) -> None:
    logger = get_main_logger("read_at_least")
    logger.info(
        "ES Read-At-Least not satisfied for user %s: applied=%s required=%s.",
        user_scope,
        not_caught_up.applied,
        not_caught_up.required,
    )


def log_recorded_es_outbox_sequence(outbox_seq: int, user_id: int) -> None:
    logger = get_main_logger("read_at_least")
    logger.debug(
        "Recorded ES applied outbox seq %s for user %s.",
        outbox_seq,
        user_id,
    )


def log_recorded_es_pending_seq(outbox_seq: int, user_id: int, event_id: str) -> None:
    logger = get_main_logger("read_at_least")
    logger.warning(
        "Search projection of outbox seq %s (event %s) failed for user %s; "
        "holding its ES Read-At-Least below it.",
        outbox_seq,
        event_id,
        user_id,
    )


def log_cleared_es_pending_seq(outbox_seq: int, user_id: int) -> None:
    logger = get_main_logger("read_at_least")
    logger.info(
        "Search projection of outbox seq %s landed for user %s; released its hold.",
        outbox_seq,
        user_id,
    )
