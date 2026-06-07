"""EntryCodec: JSON encode/decode for in-flight and completed slots.

EntryCodec defines the wire format the entire idempotency layer round-trips
through Redis. These tests pin both the structural shape and the lenient
decode behavior (junk → None) so callers can safely treat decode failure
as "no entry".
"""

from __future__ import annotations

import json

from django.test import SimpleTestCase

from write_service.common.idempotency.atomic_redis.entry_codec import (
    STATE_COMPLETED,
    STATE_IN_FLIGHT,
    EntryCodec,
)


class EncodeLockEntryTests(SimpleTestCase):
    def test_emits_in_flight_state_with_request_hash(self) -> None:
        encoded = EntryCodec.encode_lock_entry("abc123")

        self.assertEqual(
            json.loads(encoded),
            {"state": STATE_IN_FLIGHT, "request_hash": "abc123"},
        )

    def test_is_compact_json_without_whitespace(self) -> None:
        # Pin compact form — Redis storage cost matters at scale.
        encoded = EntryCodec.encode_lock_entry("h")

        self.assertNotIn(" ", encoded)


class EncodeCompletedEntryTests(SimpleTestCase):
    def test_includes_all_fields(self) -> None:
        encoded = EntryCodec.encode_completed_entry(
            request_hash="h1",
            status_code=201,
            body={"id": 1},
            headers={"X-Foo": "bar"},
        )

        decoded = json.loads(encoded)
        self.assertEqual(decoded["state"], STATE_COMPLETED)
        self.assertEqual(decoded["request_hash"], "h1")
        self.assertEqual(decoded["status_code"], 201)
        self.assertEqual(decoded["body"], {"id": 1})
        self.assertEqual(decoded["headers"], {"X-Foo": "bar"})

    def test_serializes_complex_drf_types_via_drf_json_encoder(self) -> None:
        # DRF responses can contain UUIDs / Decimals / datetimes.
        # Pin that the codec uses DRF's encoder (which stringifies them).
        from datetime import datetime
        from decimal import Decimal
        from uuid import UUID

        body = {
            "id": UUID("11111111-1111-1111-1111-111111111111"),
            "amount": Decimal("12.50"),
            "at": datetime(2026, 1, 1, 0, 0, 0),
        }

        encoded = EntryCodec.encode_completed_entry(
            request_hash="h",
            status_code=200,
            body=body,
            headers={},
        )

        decoded = json.loads(encoded)
        self.assertEqual(decoded["body"]["id"], "11111111-1111-1111-1111-111111111111")
        # DRF's JSONEncoder serializes Decimal via float() — preserves
        # number-ness but loses trailing-zero precision. Pin this so a
        # future swap to a string-preserving encoder is intentional.
        self.assertEqual(decoded["body"]["amount"], 12.5)
        # datetime is rendered as ISO string by DRF's encoder
        self.assertIn("2026-01-01", decoded["body"]["at"])


class DecodeEntryTests(SimpleTestCase):
    def test_none_input_returns_none(self) -> None:
        self.assertIsNone(EntryCodec.decode_entry(None))

    def test_bytes_input_is_utf8_decoded_first(self) -> None:
        payload = EntryCodec.encode_lock_entry("h")

        decoded = EntryCodec.decode_entry(payload.encode("utf-8"))

        self.assertEqual(decoded, {"state": STATE_IN_FLIGHT, "request_hash": "h"})

    def test_str_input_is_parsed(self) -> None:
        payload = EntryCodec.encode_lock_entry("h")

        self.assertEqual(
            EntryCodec.decode_entry(payload),
            {"state": STATE_IN_FLIGHT, "request_hash": "h"},
        )

    def test_invalid_json_returns_none_not_raise(self) -> None:
        # Lenient: callers treat None as "no usable entry".
        self.assertIsNone(EntryCodec.decode_entry("not-json"))

    def test_invalid_json_bytes_returns_none(self) -> None:
        # Valid UTF-8 but not valid JSON: decode → None.
        self.assertIsNone(EntryCodec.decode_entry(b"not json either"))
