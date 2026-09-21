from logging import Logger, getLogger

from .config import LoggerSettings


def get_service_logger(*chunks: str) -> Logger:
    return getLogger(".".join([LoggerSettings.ROOT, *chunks]))
