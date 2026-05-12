import unittest

from correlation.utilities.config import DEFAULT_HEADER_NAME, resolve_header_name
from django.test import override_settings


class ResolveHeaderNameTests(unittest.TestCase):
    def test_falls_back_to_default_when_setting_missing(self) -> None:
        with override_settings():
            from django.conf import settings

            if hasattr(settings, "CORRELATION_ID_HEADER"):
                delattr(settings, "CORRELATION_ID_HEADER")
            self.assertEqual(resolve_header_name(), DEFAULT_HEADER_NAME)

    def test_uses_value_from_settings_when_present(self) -> None:
        with override_settings(CORRELATION_ID_HEADER="X-Trace-ID"):
            self.assertEqual(resolve_header_name(), "X-Trace-ID")

    def test_default_constant_is_canonical_header(self) -> None:
        self.assertEqual(DEFAULT_HEADER_NAME, "X-Correlation-ID")
