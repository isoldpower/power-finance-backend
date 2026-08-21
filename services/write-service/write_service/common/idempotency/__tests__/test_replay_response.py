"""ReplayResponseBuilder: rebuild a Response from a StoredResponse and tag it as replayed."""

from __future__ import annotations

from django.test import SimpleTestCase

from write_service.common.idempotency.atomic_redis.outcomes import StoredResponse
from write_service.common.idempotency.replay_response import (
    REPLAY_HEADER,
    ReplayResponseBuilder,
)


class ReplayResponseBuilderTests(SimpleTestCase):
    def test_preserves_status_code_and_body(self) -> None:
        stored = StoredResponse(
            status_code=201,
            body={"data": {"id": 1}, "meta": {"idempotent_replay": False}},
            headers={},
            request_hash="h",
        )

        rebuilt = ReplayResponseBuilder.build(stored)

        self.assertEqual(rebuilt.status_code, 201)
        self.assertEqual(rebuilt.data["data"], {"id": 1})

    def test_marks_the_body_as_a_replay(self) -> None:
        """`meta.idempotent_replay` is the contract; the header is a convenience."""

        stored = StoredResponse(
            status_code=201,
            body={"data": {"id": 1}, "meta": {"idempotent_replay": False}},
            headers={},
            request_hash="h",
        )

        rebuilt = ReplayResponseBuilder.build(stored)

        self.assertIs(rebuilt.data["meta"]["idempotent_replay"], True)

    def test_adds_idempotent_replayed_header(self) -> None:
        stored = StoredResponse(status_code=200, body={}, headers={}, request_hash="h")

        rebuilt = ReplayResponseBuilder.build(stored)

        self.assertEqual(rebuilt[REPLAY_HEADER], "true")

    def test_propagates_stored_headers(self) -> None:
        stored = StoredResponse(
            status_code=200,
            body={},
            headers={"X-Custom": "abc"},
            request_hash="h",
        )

        rebuilt = ReplayResponseBuilder.build(stored)

        self.assertEqual(rebuilt["X-Custom"], "abc")

    def test_replay_header_overrides_stored_header_with_same_name(self) -> None:
        stored = StoredResponse(
            status_code=200,
            body={},
            headers={REPLAY_HEADER: "false"},
            request_hash="h",
        )

        rebuilt = ReplayResponseBuilder.build(stored)

        self.assertEqual(rebuilt[REPLAY_HEADER], "true")
