from data_read_core.shared.logging import get_main_logger


def log_provider_failed(provider: str, base_code: str | None, failure: Exception) -> None:
    logger = get_main_logger("exchange_rates")
    logger.warning(
        "Rate provider %s could not answer for %s: %s",
        provider,
        base_code,
        failure,
    )


def log_provider_refused(provider: str, base_code: str, error_type: str | None) -> None:
    logger = get_main_logger("exchange_rates")
    logger.info(
        "Rate provider %s refused base %s: %s",
        provider,
        base_code,
        error_type or "no reason given",
    )


def log_static_provider_selected() -> None:
    logger = get_main_logger("exchange_rates")
    logger.warning(
        "Exchange rates are served by the STATIC provider. Its numbers are "
        "fixed placeholders, not quotes."
    )


def log_served_from_cache(base_code: str) -> None:
    logger = get_main_logger("exchange_rates")
    logger.debug("Served rates for %s from cache.", base_code)


def log_snapshot_too_old(base_code: str, age_seconds: float, max_age_seconds: int) -> None:
    logger = get_main_logger("exchange_rates")
    logger.warning(
        "Rates for %s are %.0fs old, past the %ss limit. Refusing to serve them.",
        base_code,
        age_seconds,
        max_age_seconds,
    )
