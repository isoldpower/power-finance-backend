"""The 507 must never reach a client.

read-service answers 507 when its projection is behind the caller's write
version, and the gateway re-issues the read against write-service. The target
says no error code covers staleness, so the 507 is an internal signal between
two of our own components — a client that ever sees one is seeing a bug.

This is the test the closing steps asked for. It passes today, but only because
the reads it cannot cover are named in `MISSING_FALLBACK` below with the reason
each one is still a hole.
"""

import pytest

from ..documents import diff_document
from ..fallback import (
    fallback_paths,
    fallback_route_for,
    gated_read_paths,
    gated_read_slices,
)
from ..gateway import plugin_config, resolve

FALLBACK_STATUS = 507

# Permanent and documented. The plugin only re-issues GETs and the write side
# has no Elasticsearch, so it cannot answer a filter tree at all. A search that
# trips the gate genuinely returns 507, and API_DIFF.md tells clients to treat
# it as "retry shortly".
SEARCH_WITHOUT_FALLBACK = frozenset({"/wallets/search", "/transactions/search", "/webhooks/search"})

# Reads that CAN answer 507 and have no write-side counterpart. The plugin
# rewrites the prefix regardless, so these do not leak the 507 — they reach a
# write-service route that does not exist and return its 404, reporting a
# resource that exists as missing.
MISSING_FALLBACK = {
    "/accounts": "accounts live in ai-service's database; write-service cannot answer them",
    "/accounts/{}": "accounts live in ai-service's database; write-service cannot answer them",
    "/metrics": "needs the whole aggregate, currency conversion included, on the write side",
}


def _covered(path: str) -> bool:
    return path in fallback_paths()


def test_the_gate_is_actually_attached_to_reads():
    """Everything below is vacuous if no view is gated."""

    assert len(gated_read_slices()) > 15


def test_the_plugin_reroutes_on_the_status_the_read_side_answers():
    config = plugin_config("read-service", "read-fallback")

    assert config is not None, "read-service has no read-fallback plugin"
    assert config["fallback_status"] == FALLBACK_STATUS


def test_the_plugin_rewrites_onto_the_prefix_the_write_side_serves():
    config = plugin_config("read-service", "read-fallback")

    assert config["read_path_prefix"] == "/api/v1"
    assert config["fallback_path_prefix"] == "/api/v1/fallback-reads"
    assert resolve(fallback_route_for("/wallets"), "GET").service == "write-service"


def test_the_fallback_route_is_reachable_only_through_the_gateway():
    """It is an internal endpoint. It is routed so the plugin can call it, but
    a client asking for it directly is asking for something the API does not
    document."""

    route = resolve("/api/v1/fallback-reads/wallets", "GET")

    assert route.service == "write-service"
    assert route.name == "write-api-v1-read"


def test_the_fallback_gets_longer_than_the_read_timeout():
    """It runs AFTER a read already spent its budget, so an equal timeout would
    make the reroute fail on a slow-but-working write side."""

    config = plugin_config("read-service", "read-fallback")

    assert config["fallback_timeout_ms"] > config["read_timeout_ms"]


@pytest.mark.parametrize(
    "path",
    sorted(gated_read_paths() - SEARCH_WITHOUT_FALLBACK - set(MISSING_FALLBACK)),
)
def test_a_gated_read_has_a_write_side_counterpart(path):
    assert _covered(path), (
        f"GET {path} can answer {FALLBACK_STATUS} and has no "
        f"{fallback_route_for(path)} to be rerouted to"
    )


@pytest.mark.parametrize(
    "path",
    sorted(MISSING_FALLBACK),
    ids=lambda path: path,
)
def test_the_known_holes_are_still_holes(path):
    """An entry that has quietly been fixed fails here, so the list cannot rot
    in that direction either — closing a hole means deleting its entry, which
    hands the path straight to
    `test_a_gated_read_has_a_write_side_counterpart` above."""

    assert not _covered(path), (
        f"GET {path} now has {fallback_route_for(path)} — " f"delete its MISSING_FALLBACK entry"
    )


@pytest.mark.parametrize("path", sorted(MISSING_FALLBACK))
def test_every_known_hole_is_a_read_that_can_actually_507(path):
    """A hole for a read that is not gated would be a stale entry, not a bug."""

    assert path in gated_read_paths()


@pytest.mark.parametrize("path", sorted(SEARCH_WITHOUT_FALLBACK))
def test_the_searches_that_can_leak_a_507_say_so_to_clients(path):
    """The one case where the status does reach a client. It is allowed only
    because API_DIFF.md tells the frontend to expect it."""

    assert path in gated_read_paths()
    assert not _covered(path)
    assert "507" in diff_document(), "the leak is not explained to clients"


def test_the_diff_names_search_as_the_endpoint_that_leaks_it():
    """A bare `507` somewhere in the document is not an explanation. Some
    passage has to tie the status to the endpoint that returns it."""

    diff = diff_document().lower()
    passages = [
        diff[max(0, at - 400) : at + 400] for at in range(len(diff)) if diff.startswith("507", at)
    ]

    assert any(
        "search" in passage for passage in passages
    ), "no passage in API_DIFF.md mentions 507 anywhere near /search"
