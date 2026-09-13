import logging

from observability import TraceContextFilter

from .utilities import get_correlation_id

MISSING_VALUE_PLACEHOLDER = "-"


class CorrelationIDFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = get_correlation_id() or MISSING_VALUE_PLACEHOLDER

        return True


__all__ = [
    "CorrelationIDFilter",
    "TraceContextFilter",
]
