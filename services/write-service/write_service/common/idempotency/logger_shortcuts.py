from write_service.common.logging import get_http_logger


def warn_store_not_configured() -> None:
    logger = get_http_logger("idempotency")
    logger.warning("idempotency.store_not_configured — skipping dedup")


def warn_store_unavailable_on_acquire(error: Exception, required: bool) -> None:
    logger = get_http_logger("idempotency")
    logger.warning(
        "idempotency.store_unavailable on acquire: %s (required=%s)",
        error,
        required,
    )


def warn_store_unavailable_on_store(error: Exception) -> None:
    logger = get_http_logger("idempotency")
    logger.warning("idempotency.store_unavailable on store: %s", error)
