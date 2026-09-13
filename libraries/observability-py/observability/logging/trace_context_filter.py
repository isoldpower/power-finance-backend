import logging

from ..context import current_span_id_hex, current_trace_id_hex
from ..sandbox import current_sandbox_id

MISSING_VALUE_PLACEHOLDER = "-"


class TraceContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.trace_id = current_trace_id_hex() or MISSING_VALUE_PLACEHOLDER
        record.span_id = current_span_id_hex() or MISSING_VALUE_PLACEHOLDER
        record.sandbox_id = current_sandbox_id() or MISSING_VALUE_PLACEHOLDER

        return True
