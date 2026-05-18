"""Canonical request fingerprint.

Stripe-style: a client may reuse an Idempotency-Key only if the *request* is
identical. We hash method + path + body so that a key paired with a different
body is rejected (422) rather than silently returning the cached response of
a different request.

Body is canonicalised by parsing JSON and re-serialising with sorted keys,
which makes hash stable across whitespace and key-order variations in the
client's serialiser.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any


def fingerprint(method: str, path: str, body: Any) -> str:
    canonical_body = _canonical_body(body)
    h = hashlib.sha256()
    h.update(method.upper().encode("utf-8"))
    h.update(b"\x00")
    h.update(path.encode("utf-8"))
    h.update(b"\x00")
    h.update(canonical_body.encode("utf-8"))
    return h.hexdigest()


def _canonical_body(body: Any) -> str:
    if body is None or body == "":
        return ""
    if isinstance(body, bytes | bytearray):
        try:
            body = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return hashlib.sha256(bytes(body)).hexdigest()
    if isinstance(body, str):
        try:
            body = json.loads(body)
        except json.JSONDecodeError:
            return body
    return json.dumps(body, sort_keys=True, separators=(",", ":"), default=str)
