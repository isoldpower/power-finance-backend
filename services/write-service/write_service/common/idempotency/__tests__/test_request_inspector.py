"""RequestInspector: extract idempotency key + user id from a request."""

from __future__ import annotations

from types import SimpleNamespace

from django.test import SimpleTestCase

from write_service.common.idempotency.request_inspector import (
    IDEMPOTENCY_HEADER,
    RequestInspector,
)


def _request(*, headers: dict[str, str] | None = None, user=None) -> SimpleNamespace:
    return SimpleNamespace(headers=headers or {}, user=user)


class ExtractIdempotencyKeyTests(SimpleTestCase):
    def test_returns_none_when_header_absent(self) -> None:
        self.assertIsNone(RequestInspector.extract_idempotency_key(_request()))

    def test_returns_none_for_empty_header(self) -> None:
        self.assertIsNone(
            RequestInspector.extract_idempotency_key(_request(headers={IDEMPOTENCY_HEADER: ""}))
        )

    def test_returns_none_for_whitespace_only_header(self) -> None:
        self.assertIsNone(
            RequestInspector.extract_idempotency_key(_request(headers={IDEMPOTENCY_HEADER: "   "}))
        )

    def test_trims_surrounding_whitespace(self) -> None:
        self.assertEqual(
            RequestInspector.extract_idempotency_key(
                _request(headers={IDEMPOTENCY_HEADER: "  abc  "})
            ),
            "abc",
        )

    def test_truncates_to_255_chars(self) -> None:
        # Bounded length protects Redis from giant keys.
        very_long = "x" * 1000
        key = RequestInspector.extract_idempotency_key(
            _request(headers={IDEMPOTENCY_HEADER: very_long})
        )

        self.assertEqual(key, "x" * 255)


class ExtractUserIdTests(SimpleTestCase):
    def test_returns_user_unique_id_when_present(self) -> None:
        request = _request(user=SimpleNamespace(unique_id=42))

        self.assertEqual(RequestInspector.extract_user_id(request), 42)

    def test_falls_back_to_anonymous_when_no_user(self) -> None:
        self.assertEqual(RequestInspector.extract_user_id(_request(user=None)), "anonymous")

    def test_falls_back_to_anonymous_when_user_has_no_unique_id(self) -> None:
        request = _request(user=SimpleNamespace())

        self.assertEqual(RequestInspector.extract_user_id(request), "anonymous")
