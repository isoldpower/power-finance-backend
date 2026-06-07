import logging
import unittest

from correlation.logging import CorrelationIDFilter
from correlation.utilities.context import attach_correlation_id, reset_correlation_id


def _make_record() -> logging.LogRecord:
    return logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="hello",
        args=None,
        exc_info=None,
    )


class CorrelationIDFilterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.filter = CorrelationIDFilter()

    def test_filter_returns_true_to_keep_record(self) -> None:
        record = _make_record()
        self.assertTrue(self.filter.filter(record))

    def test_injects_placeholder_when_id_missing(self) -> None:
        record = _make_record()
        self.filter.filter(record)
        self.assertEqual(record.correlation_id, "-")

    def test_injects_active_correlation_id_when_set(self) -> None:
        token = attach_correlation_id("trace-42")
        try:
            record = _make_record()
            self.filter.filter(record)
            self.assertEqual(record.correlation_id, "trace-42")
        finally:
            reset_correlation_id(token)
