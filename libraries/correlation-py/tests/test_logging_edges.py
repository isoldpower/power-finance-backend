"""CorrelationIDFilter: edge behaviors not covered by the happy-path test.

Covers:
- the filter overwrites an existing correlation_id attribute (no merge,
  no preserve-if-set semantics);
- integration with a formatter that interpolates %(correlation_id)s,
  proving the attribute is actually usable from logging configuration.
"""

from __future__ import annotations

import io
import logging
import unittest

from correlation.logging import CorrelationIDFilter
from correlation.utilities.context import attach_correlation_id, reset_correlation_id


def _record() -> logging.LogRecord:
    return logging.LogRecord(
        name="t",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="msg",
        args=None,
        exc_info=None,
    )


class FilterEdgeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.filter = CorrelationIDFilter()

    def test_overwrites_existing_correlation_id_attr_on_record(self) -> None:
        # Defensive: if a downstream filter set correlation_id earlier,
        # ours stomps it. Pin this so a "preserve if set" change is intentional.
        record = _record()
        record.correlation_id = "stale-from-elsewhere"

        self.filter.filter(record)

        self.assertEqual(record.correlation_id, "-")

    def test_overwrites_with_active_id_even_if_record_had_one(self) -> None:
        token = attach_correlation_id("active")
        try:
            record = _record()
            record.correlation_id = "stale"

            self.filter.filter(record)

            self.assertEqual(record.correlation_id, "active")
        finally:
            reset_correlation_id(token)

    def test_works_end_to_end_through_a_handler_and_formatter(self) -> None:
        # Wire the filter into the logging stack the way consumers do
        # and verify %(correlation_id)s renders the active id.
        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        handler.addFilter(CorrelationIDFilter())
        handler.setFormatter(logging.Formatter("[%(correlation_id)s] %(message)s"))

        logger = logging.getLogger("correlation.tests.edges")
        logger.handlers = [handler]
        logger.setLevel(logging.INFO)
        logger.propagate = False

        token = attach_correlation_id("trace-xyz")
        try:
            logger.info("hello world")
        finally:
            reset_correlation_id(token)

        handler.flush()
        self.assertIn("[trace-xyz] hello world", stream.getvalue())

    def test_placeholder_dash_when_no_id_in_context(self) -> None:
        # Same as the happy-path test but proves through a formatter so
        # the placeholder isn't accidentally None / empty / falsy garbage.
        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        handler.addFilter(CorrelationIDFilter())
        handler.setFormatter(logging.Formatter("[%(correlation_id)s] %(message)s"))

        logger = logging.getLogger("correlation.tests.placeholder")
        logger.handlers = [handler]
        logger.setLevel(logging.INFO)
        logger.propagate = False

        logger.info("no-context")

        handler.flush()
        self.assertIn("[-] no-context", stream.getvalue())
