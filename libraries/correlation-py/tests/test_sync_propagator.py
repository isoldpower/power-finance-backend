import re
import unittest
import uuid

from correlation.context_propagator import SyncContextPropagator
from correlation.utilities.context import get_correlation_id
from django.http import HttpResponse
from django.test import RequestFactory

UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


class SyncContextPropagatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.factory = RequestFactory()
        self.header_name = "X-Correlation-ID"
        self.captured_id_during_request: str | None = None

    def _make_get_response(self):
        def get_response(request) -> HttpResponse:
            self.captured_id_during_request = get_correlation_id()
            return HttpResponse(status=200)

        return get_response

    def test_uses_correlation_id_from_request_header(self) -> None:
        propagator = SyncContextPropagator(self._make_get_response(), self.header_name)
        request = self.factory.get("/", HTTP_X_CORRELATION_ID="external-cid")

        response = propagator(request)

        self.assertEqual(request.correlation_id, "external-cid")
        self.assertEqual(self.captured_id_during_request, "external-cid")
        self.assertEqual(response[self.header_name], "external-cid")

    def test_generates_uuid_when_header_missing(self) -> None:
        propagator = SyncContextPropagator(self._make_get_response(), self.header_name)
        request = self.factory.get("/")

        response = propagator(request)

        self.assertIsNotNone(request.correlation_id)
        self.assertTrue(UUID_RE.match(request.correlation_id))
        uuid.UUID(request.correlation_id)
        self.assertEqual(response[self.header_name], request.correlation_id)

    def test_correlation_id_is_reset_after_response(self) -> None:
        propagator = SyncContextPropagator(self._make_get_response(), self.header_name)
        request = self.factory.get("/", HTTP_X_CORRELATION_ID="reset-me")

        propagator(request)

        self.assertIsNone(get_correlation_id())

    def test_correlation_id_resets_even_when_view_raises(self) -> None:
        def raising_get_response(_request):
            raise RuntimeError("boom")

        propagator = SyncContextPropagator(raising_get_response, self.header_name)
        request = self.factory.get("/", HTTP_X_CORRELATION_ID="cleanup-me")

        with self.assertRaises(RuntimeError):
            propagator(request)

        self.assertIsNone(get_correlation_id())

    def test_custom_header_name_is_honoured(self) -> None:
        propagator = SyncContextPropagator(self._make_get_response(), "X-Trace-ID")
        request = self.factory.get("/", HTTP_X_TRACE_ID="custom-name")

        response = propagator(request)

        self.assertEqual(request.correlation_id, "custom-name")
        self.assertEqual(response["X-Trace-ID"], "custom-name")
