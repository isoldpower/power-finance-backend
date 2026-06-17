"""ContextPropagator base class: abstract surface contract."""

from __future__ import annotations

import unittest

from correlation.context_propagator.base import ContextPropagator


class ContextPropagatorBaseTests(unittest.TestCase):
    def test_cannot_be_instantiated_directly(self) -> None:
        with self.assertRaises(TypeError):
            ContextPropagator(lambda req: None, "X-Correlation-ID")  # type: ignore[abstract]

    def test_subclass_without_call_implementation_is_still_abstract(self) -> None:
        class _Incomplete(ContextPropagator):
            pass

        with self.assertRaises(TypeError):
            _Incomplete(lambda req: None, "X-Correlation-ID")  # type: ignore[abstract]

    def test_subclass_with_call_implementation_initialises_and_stores_attrs(self) -> None:
        class _Minimal(ContextPropagator):
            def __call__(self, request):  # type: ignore[override]
                return None

        get_response = lambda request: None  # noqa: E731

        propagator = _Minimal(get_response, "X-Trace")

        self.assertIs(propagator.get_response, get_response)
        self.assertEqual(propagator.header_name, "X-Trace")
