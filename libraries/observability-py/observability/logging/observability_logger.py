import logging

LOGGER_NAMESPACE = "observability"


def get_observability_logger(child_name: str | None = None) -> logging.Logger:
    if child_name:
        return logging.getLogger(f"{LOGGER_NAMESPACE}.{child_name}")

    return logging.getLogger(LOGGER_NAMESPACE)
