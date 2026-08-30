from logging import Logger, getLogger

LOGGER_ROOT = "ai_service"


def get_service_logger(*chunks: str) -> Logger:
    return getLogger(".".join([LOGGER_ROOT, *chunks]))
