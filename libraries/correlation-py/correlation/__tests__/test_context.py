import unittest

from correlation.utilities.context import (
    attach_correlation_id,
    get_correlation_id,
    reset_correlation_id,
)


class CorrelationContextTests(unittest.TestCase):
    def tearDown(self) -> None:
        token = attach_correlation_id("__cleanup__")
        reset_correlation_id(token)

    def test_get_returns_none_when_unset(self) -> None:
        self.assertIsNone(get_correlation_id())

    def test_attach_then_get_returns_value(self) -> None:
        token = attach_correlation_id("abc-123")
        try:
            self.assertEqual(get_correlation_id(), "abc-123")
        finally:
            reset_correlation_id(token)

    def test_reset_restores_previous_value(self) -> None:
        outer_token = attach_correlation_id("outer")
        inner_token = attach_correlation_id("inner")
        self.assertEqual(get_correlation_id(), "inner")

        reset_correlation_id(inner_token)
        self.assertEqual(get_correlation_id(), "outer")

        reset_correlation_id(outer_token)
        self.assertIsNone(get_correlation_id())

    def test_attach_overwrites_current_value(self) -> None:
        first = attach_correlation_id("first")
        second = attach_correlation_id("second")
        try:
            self.assertEqual(get_correlation_id(), "second")
        finally:
            reset_correlation_id(second)
            reset_correlation_id(first)
