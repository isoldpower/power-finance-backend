from service_core.shared.logging import get_service_logger

from ..application.config import LoggerSettings


def log_provider_failed(provider: str, base_code: object, failure: object) -> None:
    logger = get_service_logger(LoggerSettings.NAME)
    logger.warning("rate feed %s failed for base %s: %s", provider, base_code, failure)


def log_provider_refused(provider: str, base_code: str, error_type: object) -> None:
    logger = get_service_logger(LoggerSettings.NAME)
    logger.warning("rate feed %s refused base %s: %s", provider, base_code, error_type)
