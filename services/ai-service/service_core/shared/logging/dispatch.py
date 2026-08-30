from .registry import get_service_logger

_logger = get_service_logger("dispatch")


def log_postings_dispatched(transaction_id: str, leg_count: int, backend: str) -> None:
    _logger.info(
        "dispatched %s legs for transaction %s via %s",
        leg_count,
        transaction_id,
        backend,
    )


def log_postings_removed(transaction_id: str) -> None:
    _logger.info("removed postings for transaction %s", transaction_id)


def debug_nothing_to_remove(transaction_id: str) -> None:
    _logger.debug("transaction %s had no postings; nothing removed", transaction_id)
