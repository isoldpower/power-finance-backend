from logging import Logger, getLogger

LOGGER_NAMESPACE = "kafka_consumer_py"


def get_consumer_logger(*chunks: str) -> Logger:
    return getLogger(".".join([LOGGER_NAMESPACE, *chunks]))
