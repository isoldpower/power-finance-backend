from logging.config import dictConfig

from service_core.shared.logging import LOGGER_ROOT


def configure_logging(level: str) -> None:
    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "filters": {
                "correlation_id": {"()": "correlation.CorrelationIDFilter"},
            },
            "formatters": {
                "standard": {
                    "format": "{levelname} {asctime} cid={correlation_id} {name} {message}",
                    "style": "{",
                },
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "standard",
                    "filters": ["correlation_id"],
                },
            },
            "loggers": {
                LOGGER_ROOT: {
                    "handlers": ["console"],
                    "level": level,
                    "propagate": False,
                },
                "kafka_consumer_py": {
                    "handlers": ["console"],
                    "level": level,
                    "propagate": False,
                },
            },
        }
    )
