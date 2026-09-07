"""API_TARGET.md, endpoint by endpoint.

The closing step this replaces was a one-off audit. As a test it also catches
the reverse drift: a route added without a line in API_DIFF.md telling the
frontend it exists.
"""

import pytest

from ..documents import is_documented_deviation, key, target_endpoints
from ..surface import public_endpoints

SERVED = {key(endpoint) for endpoint in public_endpoints()}
TARGETED = {key(endpoint) for endpoint in target_endpoints()}


def test_the_target_document_still_parses_into_endpoints():
    """Every assertion below is vacuous if the headings stop matching."""

    assert len(target_endpoints()) > 40


@pytest.mark.parametrize("endpoint", target_endpoints(), ids=str)
def test_every_target_endpoint_is_served_or_explained(endpoint):
    """One of two things has to be true of every documented endpoint: it exists,
    or API_DIFF.md tells the frontend what replaced it."""

    if key(endpoint) in SERVED:
        return

    assert is_documented_deviation(endpoint), (
        f"{endpoint} is in API_TARGET.md, is not served, and is not mentioned in "
        "API_DIFF.md — a client would find it documented and get a bare 404"
    )


@pytest.mark.parametrize("endpoint", public_endpoints(), ids=str)
def test_every_served_endpoint_is_targeted_or_explained(endpoint):
    """An addition is allowed — the versioning rules call it additive — but it
    has to be written down, or the only way to find it is to read the code."""

    if key(endpoint) in TARGETED:
        return

    assert is_documented_deviation(endpoint), (
        f"{endpoint} is served, is not in API_TARGET.md, and is not mentioned in "
        "API_DIFF.md — an endpoint nobody outside this repository knows about"
    )


def test_the_metrics_slice_collapsed_into_one_endpoint():
    """The target spends three endpoints on figures a panel always shows
    together. Pinned because it is the largest single deviation in the surface,
    and re-splitting it would be a breaking change either way."""

    assert ("GET", "/metrics") in SERVED
    for replaced in ("/metrics/balance", "/metrics/net-worth", "/metrics/cash-flow"):
        assert ("GET", replaced) not in SERVED


def test_sending_a_message_is_the_socket_rather_than_the_documented_post():
    """Decided with the user: the reply streams over the WebSocket that already
    existed, carrying the target's own event vocabulary."""

    assert ("POST", "/assistant/messages") not in SERVED
    assert ("GET", "/chat/advice") in SERVED
