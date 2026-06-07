"""Public API surface: `correlation` re-exports the documented names.

These names are what downstream services import. Renaming or removing
one is a breaking change — pin the surface so accidental refactors get
caught at the library boundary rather than at every consumer's CI.
"""

from __future__ import annotations

import unittest

import correlation


class PublicApiTests(unittest.TestCase):
    def test_all_lists_the_documented_names(self) -> None:
        self.assertEqual(
            set(correlation.__all__),
            {
                "CorrelationIDFilter",
                "CorrelationIDMiddleware",
                "get_correlation_id",
                "resolve_header_name",
            },
        )

    def test_correlation_id_filter_is_re_exported(self) -> None:
        from correlation.logging import CorrelationIDFilter

        self.assertIs(correlation.CorrelationIDFilter, CorrelationIDFilter)

    def test_correlation_id_middleware_is_re_exported(self) -> None:
        from correlation.middleware import CorrelationIDMiddleware

        self.assertIs(correlation.CorrelationIDMiddleware, CorrelationIDMiddleware)

    def test_get_correlation_id_is_re_exported(self) -> None:
        from correlation.utilities import get_correlation_id

        self.assertIs(correlation.get_correlation_id, get_correlation_id)

    def test_resolve_header_name_is_re_exported(self) -> None:
        from correlation.utilities import resolve_header_name

        self.assertIs(correlation.resolve_header_name, resolve_header_name)
