from service_core.shared.logging import get_service_logger

from .config import LoggerSettings


def log_snapshot_too_old(base_code: str, age_seconds: float, max_age_seconds: int) -> None:
    logger = get_service_logger(LoggerSettings.NAME)
    logger.warning(
        "rates for %s are %.0fs old, past the %ss limit; refusing to book against them",
        base_code,
        age_seconds,
        max_age_seconds,
    )


def log_rates_fetched(base_code: str, quoted: int) -> None:
    logger = get_service_logger(LoggerSettings.NAME)
    logger.info("fetched %s rates quoted against %s", quoted, base_code)
