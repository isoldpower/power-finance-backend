from service_core.shared.logging import get_service_logger

LOGGER_NAME = "exchange_rates"


def log_provider_failed(provider: str, base_code: object, failure: object) -> None:
    logger = get_service_logger(LOGGER_NAME)
    logger.warning("rate feed %s failed for base %s: %s", provider, base_code, failure)


def log_provider_refused(provider: str, base_code: str, error_type: object) -> None:
    logger = get_service_logger(LOGGER_NAME)
    logger.warning("rate feed %s refused base %s: %s", provider, base_code, error_type)


def log_snapshot_too_old(base_code: str, age_seconds: float, max_age_seconds: int) -> None:
    logger = get_service_logger(LOGGER_NAME)
    logger.warning(
        "rates for %s are %.0fs old, past the %ss limit; refusing to book against them",
        base_code,
        age_seconds,
        max_age_seconds,
    )


def log_rates_fetched(base_code: str, quoted: int) -> None:
    logger = get_service_logger(LOGGER_NAME)
    logger.info("fetched %s rates quoted against %s", quoted, base_code)
