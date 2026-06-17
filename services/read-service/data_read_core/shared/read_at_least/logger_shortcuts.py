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
