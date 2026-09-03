"""One opaque cursor, four implementations that must agree.

Every service keeps its own codec — the house pattern for shared conventions —
and webhook-service reimplements the format in Go. A client stores one token
and sends it back to whichever service answers, so a difference of one byte in
any of them is a page a client cannot turn.

The golden token is written down rather than round-tripped, because a round
trip through a single codec passes even when all four have drifted together.
"""

import base64
import json

import pytest

from ..cursors import (
    FILTERED_ORDERS,
    GOLDEN_DIRECTION,
    GOLDEN_ORDER,
    GOLDEN_VALUES,
    filtered_collections,
    go_source,
    minted,
)

SERVICES = tuple(minted())
GOLDEN_TOKEN = minted()["read-service"]["token"]

PAYLOAD_KEYS = {"v", "d", "k", "f"}


def _decode(token: str) -> dict:
    padded = token + "=" * (-len(token) % 4)

    return json.loads(base64.urlsafe_b64decode(padded.encode()))


@pytest.mark.parametrize("service", SERVICES)
def test_every_service_mints_the_same_token_for_the_same_position(service):
    assert (
        minted()[service]["token"] == GOLDEN_TOKEN
    ), f"{service} mints a different cursor than read-service for one position"


@pytest.mark.parametrize("service", SERVICES)
def test_every_service_computes_the_same_fingerprint(service):
    """The fingerprint binds a cursor to its query. Two services disagreeing on
    it would reject each other's cursors as `cursor_mismatch`."""

    assert minted()[service]["fingerprint"] == minted()["read-service"]["fingerprint"]


@pytest.mark.parametrize("service", SERVICES)
def test_every_service_spells_the_default_order_the_same_way(service):
    """`created_at DESC, id DESC` is the global order, and its spelling is
    hashed into the fingerprint — so the string itself is contract."""

    assert minted()[service]["order"] == GOLDEN_ORDER


def test_the_token_is_unpadded_url_safe_base64():
    """It travels in a query string, so `+`, `/` and `=` would all need
    escaping and a client would have to know to do it."""

    assert "=" not in GOLDEN_TOKEN
    assert "+" not in GOLDEN_TOKEN
    assert "/" not in GOLDEN_TOKEN


def test_the_payload_is_the_agreed_four_keys():
    payload = _decode(GOLDEN_TOKEN)

    assert set(payload) == PAYLOAD_KEYS
    assert payload["v"] == 1
    assert payload["d"] == GOLDEN_DIRECTION
    assert payload["k"] == GOLDEN_VALUES


def test_the_timestamp_travels_with_an_explicit_offset():
    """A naive timestamp inside a cursor is a keyset anchor that means something
    different depending on who reads it."""

    timestamp = _decode(GOLDEN_TOKEN)["k"][0]

    assert timestamp.endswith("+00:00")


def test_the_go_implementation_pins_the_same_golden_token():
    """It cannot be driven from here — it is a different language and its
    encoder is package-internal — so `go test` owns the assertion and this
    checks the two goldens are the same string."""

    assert GOLDEN_TOKEN in go_source(), (
        "webhook-service's Go cursor test does not pin the token the Python "
        "services mint; the two goldens have drifted"
    )


def test_the_go_implementation_agrees_on_the_shared_constants():
    source = go_source()

    assert f'OrderSignature    = "{GOLDEN_ORDER}"' in source or GOLDEN_ORDER in source
    assert "CursorVersion" in source
    for shared_key in sorted(PAYLOAD_KEYS):
        assert (
            f'json:"{shared_key}"' in source
        ), f"the Go payload does not carry the {shared_key!r} key"


@pytest.mark.parametrize("collection", sorted(FILTERED_ORDERS))
def test_the_two_sides_bind_a_filtered_cursor_to_the_same_material(collection):
    """`/actions` and `/automations` are the two reroutable reads whose cursor
    fingerprint covers filters as well as sort order. read-service mints the
    token, and after a stale read the gateway hands that exact token to
    write-service — which rebuilds the fingerprint from its own filter object.
    A single renamed key there turns a working page into a cursor mismatch."""

    bound = filtered_collections()

    assert (
        bound["read-service"][collection]["material"]
        == bound["write-service"][collection]["material"]
    ), (
        f"the {collection} filter material differs between the services, so a "
        f"cursor minted on one is rejected by the other"
    )


@pytest.mark.parametrize("collection", sorted(FILTERED_ORDERS))
def test_the_two_sides_serve_a_filtered_collection_in_the_same_order(collection):
    """The other half of the fingerprint. Ordering also has to match for the
    rerouted page to continue where the client left off rather than restart."""

    bound = filtered_collections()

    for service in ("read-service", "write-service"):
        assert bound[service][collection]["order"] == FILTERED_ORDERS[collection], (
            f"{service} serves {collection} in a different order than the " f"reroute assumes"
        )
