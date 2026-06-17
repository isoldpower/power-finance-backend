"""Edge cases for sync + async propagators that aren't covered by the
happy-path tests.

These pin behavior that's easy to break by a careless refactor:
- ordering (request.correlation_id assigned BEFORE the view runs, so the
  view can read it; ContextVar visible inside the view; reset happens
  AFTER the view returns, before the header is stamped on the response)
- header-fallback semantics (empty string falls through to UUID, since
  the implementation uses `or`)
- non-UUID inbound IDs are preserved verbatim — the library is a
  passthrough, not a validator
- per-request isolation: a request that fails to provide an ID gets a
  fresh UUID and does not leak the previous request's ID
- response header is only stamped when get_response returns; on raise,
  there's no response to stamp and the context is still cleaned up
"""

from __future__ import annotations

import unittest
import uuid

from django.http import HttpResponse
from django.test import RequestFactory

from correlation.context_propagator import (
    AsyncContextPropagator,
    SyncContextPropagator,
)
from correlation.utilities.context import get_correlation_id

HEADER = "X-Correlation-ID"


class SyncPropagatorEdgeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.factory = RequestFactory()

    def test_empty_string_header_falls_through_to_generated_uuid(self) -> None:
        captured: dict[str, str | None] = {}

        def get_response(request):
            captured["seen"] = request.correlation_id
            return HttpResponse(status=200)

        propagator = SyncContextPropagator(get_response, HEADER)
        request = self.factory.get("/", HTTP_X_CORRELATION_ID="")

        response = propagator(request)

        self.assertIsNotNone(captured["seen"])
        uuid.UUID(captured["seen"])
        self.assertEqual(response[HEADER], captured["seen"])

    def test_non_uuid_inbound_id_is_preserved_verbatim(self) -> None:
        propagator = SyncContextPropagator(lambda req: HttpResponse(status=200), HEADER)
        request = self.factory.get("/", HTTP_X_CORRELATION_ID="not-a-uuid-12345")

        response = propagator(request)

        self.assertEqual(request.correlation_id, "not-a-uuid-12345")
        self.assertEqual(response[HEADER], "not-a-uuid-12345")

    def test_request_correlation_id_is_assigned_before_view_runs(self) -> None:
        captured: dict[str, str] = {}

        def get_response(request):
            captured["attr"] = request.correlation_id
            return HttpResponse(status=200)

        propagator = SyncContextPropagator(get_response, HEADER)
        request = self.factory.get("/", HTTP_X_CORRELATION_ID="set-first")

        propagator(request)

        self.assertEqual(captured["attr"], "set-first")

    def test_contextvar_is_visible_inside_view(self) -> None:
        captured: dict[str, str | None] = {}

        def get_response(_request):
            captured["ctx"] = get_correlation_id()
            return HttpResponse(status=200)

        propagator = SyncContextPropagator(get_response, HEADER)
        request = self.factory.get("/", HTTP_X_CORRELATION_ID="ctx-visible")

        propagator(request)

        self.assertEqual(captured["ctx"], "ctx-visible")

    def test_on_view_exception_response_header_is_not_set(self) -> None:
        def raising(_request):
            raise RuntimeError("boom")

        propagator = SyncContextPropagator(raising, HEADER)
        request = self.factory.get("/", HTTP_X_CORRELATION_ID="x")

        with self.assertRaises(RuntimeError):
            propagator(request)

        self.assertIsNone(get_correlation_id())

    def test_two_sequential_requests_get_independent_generated_ids(self) -> None:
        seen_ids: list[str] = []

        def get_response(request):
            seen_ids.append(request.correlation_id)
            return HttpResponse(status=200)

        propagator = SyncContextPropagator(get_response, HEADER)
        propagator(self.factory.get("/"))
        propagator(self.factory.get("/"))

        self.assertEqual(len(set(seen_ids)), 2)

    def test_contextvar_is_reset_to_none_between_requests(self) -> None:
        propagator = SyncContextPropagator(lambda req: HttpResponse(status=200), HEADER)

        propagator(self.factory.get("/", HTTP_X_CORRELATION_ID="first"))
        self.assertIsNone(get_correlation_id())
        propagator(self.factory.get("/", HTTP_X_CORRELATION_ID="second"))
        self.assertIsNone(get_correlation_id())


class AsyncPropagatorEdgeTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.factory = RequestFactory()

    async def test_empty_string_header_falls_through_to_generated_uuid(self) -> None:
        captured: dict[str, str | None] = {}

        async def get_response(request):
            captured["seen"] = request.correlation_id
            return HttpResponse(status=200)

        propagator = AsyncContextPropagator(get_response, HEADER)
        request = self.factory.get("/", HTTP_X_CORRELATION_ID="")

        response = await propagator(request)

        uuid.UUID(captured["seen"])
        self.assertEqual(response[HEADER], captured["seen"])

    async def test_non_uuid_inbound_id_is_preserved_verbatim(self) -> None:
        async def get_response(_request):
            return HttpResponse(status=200)

        propagator = AsyncContextPropagator(get_response, HEADER)
        request = self.factory.get("/", HTTP_X_CORRELATION_ID="arbitrary-id")

        response = await propagator(request)

        self.assertEqual(request.correlation_id, "arbitrary-id")
        self.assertEqual(response[HEADER], "arbitrary-id")

    async def test_contextvar_is_visible_inside_async_view(self) -> None:
        captured: dict[str, str | None] = {}

        async def get_response(_request):
            captured["ctx"] = get_correlation_id()
            return HttpResponse(status=200)

        propagator = AsyncContextPropagator(get_response, HEADER)
        request = self.factory.get("/", HTTP_X_CORRELATION_ID="ctx-async")

        await propagator(request)

        self.assertEqual(captured["ctx"], "ctx-async")

    async def test_two_sequential_requests_get_independent_generated_ids(self) -> None:
        seen_ids: list[str] = []

        async def get_response(request):
            seen_ids.append(request.correlation_id)
            return HttpResponse(status=200)

        propagator = AsyncContextPropagator(get_response, HEADER)
        await propagator(self.factory.get("/"))
        await propagator(self.factory.get("/"))

        self.assertEqual(len(set(seen_ids)), 2)
