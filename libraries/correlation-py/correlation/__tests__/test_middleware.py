import unittest

from asgiref.sync import iscoroutinefunction
from django.http import HttpResponse
from django.test import RequestFactory, override_settings

from correlation.context_propagator import (
    AsyncContextPropagator,
    SyncContextPropagator,
)
from correlation.middleware import CorrelationIDMiddleware


def _sync_get_response(_request) -> HttpResponse:
    return HttpResponse(status=200)


async def _async_get_response(_request) -> HttpResponse:
    return HttpResponse(status=200)


class CorrelationIDMiddlewareSyncTests(unittest.TestCase):
    def setUp(self) -> None:
        self.factory = RequestFactory()

    def test_picks_sync_propagator_for_sync_get_response(self) -> None:
        middleware = CorrelationIDMiddleware(_sync_get_response)
        self.assertIsInstance(middleware._propagator, SyncContextPropagator)
        self.assertFalse(iscoroutinefunction(middleware))

    def test_dispatches_sync_request_end_to_end(self) -> None:
        middleware = CorrelationIDMiddleware(_sync_get_response)
        request = self.factory.get("/", HTTP_X_CORRELATION_ID="end-to-end")

        response = middleware(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["X-Correlation-ID"], "end-to-end")
        self.assertEqual(request.correlation_id, "end-to-end")

    @override_settings(CORRELATION_ID_HEADER="X-Trace-ID")
    def test_custom_header_from_settings_is_used(self) -> None:
        middleware = CorrelationIDMiddleware(_sync_get_response)
        request = self.factory.get("/", HTTP_X_TRACE_ID="cfg-header")

        response = middleware(request)

        self.assertEqual(response["X-Trace-ID"], "cfg-header")


class CorrelationIDMiddlewareAsyncTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.factory = RequestFactory()

    def test_picks_async_propagator_for_async_get_response(self) -> None:
        middleware = CorrelationIDMiddleware(_async_get_response)
        self.assertIsInstance(middleware._propagator, AsyncContextPropagator)
        self.assertTrue(iscoroutinefunction(middleware))

    async def test_dispatches_async_request_end_to_end(self) -> None:
        middleware = CorrelationIDMiddleware(_async_get_response)
        request = self.factory.get("/", HTTP_X_CORRELATION_ID="async-cid")

        response = await middleware(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["X-Correlation-ID"], "async-cid")
        self.assertEqual(request.correlation_id, "async-cid")
