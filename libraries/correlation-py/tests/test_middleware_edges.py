"""CorrelationIDMiddleware: picker edges + header-resolved-at-construction.

Django's middleware framework instantiates the middleware once per
process and reuses it. The header name is resolved ONCE at __init__
time, so changing CORRELATION_ID_HEADER after the middleware has been
constructed does NOT affect already-instantiated instances. Pin this.

Also pin that the sync/async picker uses asgiref's iscoroutinefunction,
which correctly handles lambdas, plain functions, and callable classes —
the three forms Django actually accepts as middleware get_response.
"""

from __future__ import annotations

import unittest

from asgiref.sync import iscoroutinefunction
from correlation.context_propagator import (
    AsyncContextPropagator,
    SyncContextPropagator,
)
from correlation.middleware import CorrelationIDMiddleware
from django.http import HttpResponse
from django.test import RequestFactory, override_settings


class _SyncCallable:
    def __call__(self, _request) -> HttpResponse:
        return HttpResponse(status=200)


class MiddlewarePickerEdgeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.factory = RequestFactory()

    def test_lambda_is_treated_as_sync(self) -> None:
        middleware = CorrelationIDMiddleware(lambda req: HttpResponse(status=200))

        self.assertIsInstance(middleware._propagator, SyncContextPropagator)
        self.assertFalse(iscoroutinefunction(middleware))

    def test_callable_class_is_treated_as_sync(self) -> None:
        middleware = CorrelationIDMiddleware(_SyncCallable())

        self.assertIsInstance(middleware._propagator, SyncContextPropagator)
        self.assertFalse(iscoroutinefunction(middleware))

    def test_async_def_is_treated_as_async(self) -> None:
        async def get_response(_request):
            return HttpResponse(status=200)

        middleware = CorrelationIDMiddleware(get_response)

        self.assertIsInstance(middleware._propagator, AsyncContextPropagator)
        self.assertTrue(iscoroutinefunction(middleware))


class MiddlewareHeaderResolutionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.factory = RequestFactory()

    def test_header_name_is_captured_at_construction_not_at_call(self) -> None:
        # Middleware is instantiated once and reused across requests.
        # If a setting flip after construction changed behavior at
        # request time, the resulting drift would be very confusing.
        with override_settings(CORRELATION_ID_HEADER="X-Build-Time"):
            middleware = CorrelationIDMiddleware(lambda req: HttpResponse(status=200))

        # Setting changes AFTER construction must not be observed.
        with override_settings(CORRELATION_ID_HEADER="X-Runtime"):
            request = self.factory.get("/", HTTP_X_BUILD_TIME="bt-id")
            response = middleware(request)

        self.assertEqual(response["X-Build-Time"], "bt-id")
        self.assertNotIn("X-Runtime", response)

    def test_default_header_is_used_when_setting_unset(self) -> None:
        # No CORRELATION_ID_HEADER → falls back to "X-Correlation-ID".
        from django.conf import settings

        had_attr = hasattr(settings, "CORRELATION_ID_HEADER")
        previous_value = getattr(settings, "CORRELATION_ID_HEADER", None)
        if had_attr:
            delattr(settings, "CORRELATION_ID_HEADER")
        try:
            middleware = CorrelationIDMiddleware(lambda req: HttpResponse(status=200))

            response = middleware(self.factory.get("/", HTTP_X_CORRELATION_ID="default-cid"))

            self.assertEqual(response["X-Correlation-ID"], "default-cid")
        finally:
            if had_attr:
                settings.CORRELATION_ID_HEADER = previous_value
