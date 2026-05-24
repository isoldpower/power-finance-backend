import logging

from .utilities import get_correlation_id


class CorrelationIDFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = get_correlation_id() or "-"

        return True
