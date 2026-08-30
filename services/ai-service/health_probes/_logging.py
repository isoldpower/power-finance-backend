from logging import Logger, getLogger

LOGGER_ROOT = "ai_service"


def get_probe_logger(*chunks: str) -> Logger:
    return getLogger(".".join([LOGGER_ROOT, *chunks]))
