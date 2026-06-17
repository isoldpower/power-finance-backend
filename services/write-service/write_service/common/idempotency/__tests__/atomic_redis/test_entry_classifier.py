"""EntryClassifier: turns a raw redis entry + the current request hash into an AcquireResult."""

from __future__ import annotations

from django.test import SimpleTestCase

from write_service.common.idempotency.atomic_redis.entry_classifier import (
    EntryClassifier,
)
from write_service.common.idempotency.atomic_redis.entry_codec import (
    STATE_COMPLETED,
    STATE_IN_FLIGHT,
)
from write_service.common.idempotency.atomic_redis.outcomes import (
    AlreadyCompleted,
    InProgress,
    Mismatch,
)


class EntryClassifierTests(SimpleTestCase):
    def test_missing_entry_is_treated_as_in_progress(self) -> None:
        outcome = EntryClassifier.classify(existing_entry=None, request_hash="h")

        self.assertIsInstance(outcome, InProgress)

    def test_different_hash_returns_mismatch_with_stored_hash(self) -> None:
        outcome = EntryClassifier.classify(
            existing_entry={"state": STATE_IN_FLIGHT, "request_hash": "stored"},
            request_hash="incoming",
        )

        self.assertIsInstance(outcome, Mismatch)
        assert isinstance(outcome, Mismatch)
        self.assertEqual(outcome.stored_hash, "stored")

    def test_matching_hash_in_flight_returns_in_progress(self) -> None:
        outcome = EntryClassifier.classify(
            existing_entry={"state": STATE_IN_FLIGHT, "request_hash": "h"},
            request_hash="h",
        )

        self.assertIsInstance(outcome, InProgress)

    def test_matching_hash_completed_returns_already_completed_with_response(self) -> None:
        outcome = EntryClassifier.classify(
            existing_entry={
                "state": STATE_COMPLETED,
                "request_hash": "h",
                "status_code": 201,
                "body": {"id": 1},
                "headers": {"X-Foo": "bar"},
            },
            request_hash="h",
        )

        self.assertIsInstance(outcome, AlreadyCompleted)
        assert isinstance(outcome, AlreadyCompleted)
        self.assertEqual(outcome.response.status_code, 201)
        self.assertEqual(outcome.response.body, {"id": 1})
        self.assertEqual(outcome.response.headers, {"X-Foo": "bar"})
        self.assertEqual(outcome.response.request_hash, "h")

    def test_completed_entry_missing_headers_defaults_to_empty_dict(self) -> None:
        outcome = EntryClassifier.classify(
            existing_entry={
                "state": STATE_COMPLETED,
                "request_hash": "h",
                "status_code": 200,
                "body": None,
            },
            request_hash="h",
        )

        assert isinstance(outcome, AlreadyCompleted)
        self.assertEqual(outcome.response.headers, {})

    def test_status_code_is_coerced_to_int(self) -> None:
        outcome = EntryClassifier.classify(
            existing_entry={
                "state": STATE_COMPLETED,
                "request_hash": "h",
                "status_code": "201",
                "body": {},
            },
            request_hash="h",
        )

        assert isinstance(outcome, AlreadyCompleted)
        self.assertEqual(outcome.response.status_code, 201)

    def test_empty_stored_hash_falls_through_to_state_check(self) -> None:
        outcome = EntryClassifier.classify(
            existing_entry={"state": STATE_IN_FLIGHT, "request_hash": ""},
            request_hash="any",
        )

        self.assertIsInstance(outcome, InProgress)
