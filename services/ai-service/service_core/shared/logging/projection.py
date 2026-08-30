from .registry import get_service_logger

_logger = get_service_logger("projection")


def log_transaction_projected(transaction_id: str) -> None:
    _logger.info(
        "projected transaction %s",
        transaction_id,
    )


def log_transaction_amount_updated(transaction_id: str) -> None:
    _logger.info(
        "updated amount on transaction %s",
        transaction_id,
    )


def log_transaction_soft_deleted(transaction_id: str) -> None:
    _logger.info(
        "soft-deleted transaction %s",
        transaction_id,
    )


def debug_stale_event_skipped(transaction_id: str, applied_seq: int, event_seq: int) -> None:
    _logger.debug(
        "skipping event for transaction %s; already applied seq %s, event carries %s",
        transaction_id,
        applied_seq,
        event_seq,
    )


def debug_unknown_transaction(transaction_id: str) -> None:
    _logger.debug(
        "no projected transaction %s; nothing to apply",
        transaction_id,
    )
