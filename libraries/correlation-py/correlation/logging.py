import logging

from .utilities import get_correlation_id


class CorrelationIDFilter(logging.Filter):
    """Inject the active correlation ID (or "-" when missing) into every log
    record as `record.correlation_id`. Wire into a LOGGING formatter with
    e.g. `format = "{levelname} {asctime} cid={correlation_id} {name} {message}"`.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = get_correlation_id() or "-"

        return True
