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
            body={"id": 1},
            headers={},
            request_hash="h",
        )

        rebuilt = ReplayResponseBuilder.build(stored)

        self.assertEqual(rebuilt.status_code, 201)
        self.assertEqual(rebuilt.data, {"id": 1})

    def test_adds_idempotent_replayed_header(self) -> None:
        # Clients use this header to differentiate "first response" from "replay".
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
        # The builder sets REPLAY_HEADER AFTER copying stored headers,
        # so a stored "Idempotent-Replayed: false" must end up as "true".
        stored = StoredResponse(
            status_code=200,
            body={},
            headers={REPLAY_HEADER: "false"},
            request_hash="h",
        )

        rebuilt = ReplayResponseBuilder.build(stored)

        self.assertEqual(rebuilt[REPLAY_HEADER], "true")
