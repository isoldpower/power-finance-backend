"""Which service the gateway would hand each request to.

The split between read and write is entirely Kong's, so a route in the wrong
place is not a 500 anyone would notice in a unit test — it is a GET answered by
a service that has no such view, or a POST answered by a projection.
"""

import pytest

from ..documents import API_PREFIX, normalise
from ..gateway import plugin_config, resolve, routes
from ..surface import GO_ROUTES, WEBSOCKET_ROUTES, public_endpoints, schema_of

MUTATING_METHODS = ("POST", "PATCH", "PUT", "DELETE")

# Reads that are POSTs. They need their own longer-prefix routes, or the write
# route claims them by method.
SEARCH_ENDPOINTS = ("/wallets/search", "/transactions/search", "/webhooks/search")

# A mutation reaches the service that OWNS the resource, which is write-service
# for everything it holds the ledger for — and is not, for the slices whose
# state lives in another service's own database.
OWNED_ELSEWHERE = {
    "/assistant": "ai-service",
}


def _owner_of(path: str) -> str:
    for prefix, service in OWNED_ELSEWHERE.items():
        if normalise(path).startswith(prefix):
            return service

    return "write-service"


def _concrete(path: str) -> str:
    """A routable path: Kong matches on prefixes and regexes, not templates."""

    return path.replace("{webhook_id}", "1665b60e-bb7a-4360-8aa6-c1a578d81077").replace(
        "{notification_id}", "7c3e9a10-4d2b-4f77-91cc-5e8b0a2f6d34"
    )


@pytest.mark.parametrize("endpoint", public_endpoints(), ids=str)
def test_every_public_endpoint_is_routed_by_the_gateway(endpoint):
    """No host port is published for any service, so a path Kong does not route
    is unreachable however well it is implemented."""

    assert (
        resolve(_concrete(endpoint.path), endpoint.method) is not None
    ), f"{endpoint} is served but nothing in kong.yml routes it"


@pytest.mark.parametrize("endpoint", public_endpoints(), ids=str)
def test_every_public_endpoint_is_authenticated(endpoint):
    """`clerk-jwt` is what turns a bearer token into the `X-User-Id` every
    service trusts. A route without it would serve anonymous callers."""

    route = resolve(_concrete(endpoint.path), endpoint.method)

    assert (
        plugin_config(route.service, "clerk-jwt") is not None
    ), f"{endpoint} routes to {route.service}, which has no clerk-jwt plugin"


@pytest.mark.parametrize(
    "endpoint",
    [endpoint for endpoint in public_endpoints() if endpoint.method in MUTATING_METHODS],
    ids=str,
)
def test_a_mutation_reaches_the_service_that_owns_the_resource(endpoint):
    """Almost always write-service, which holds the ledger. The exception is a
    slice whose state lives in another service's own Postgres — routing its
    DELETE to write-service would hand it to a service with no such table."""

    if normalise(endpoint.path) in SEARCH_ENDPOINTS:
        return

    route = resolve(_concrete(endpoint.path), endpoint.method)

    assert route.service == _owner_of(
        endpoint.path
    ), f"{endpoint} would reach {route.service} via route {route.name!r}"


def test_the_conversation_is_cleared_by_the_service_that_stores_it():
    """Pinned separately because it is the only mutation that does NOT go to
    write-service, and a broad `methods: [POST, PATCH, DELETE]` write route
    would quietly capture it."""

    assert resolve(f"{API_PREFIX}/assistant/messages", "DELETE").service == "ai-service"


@pytest.mark.parametrize("path", SEARCH_ENDPOINTS)
def test_search_is_a_post_that_reaches_the_read_side(path):
    """A search is a read with a body. It has to beat the write route, which
    claims every POST on the shared prefix."""

    route = resolve(f"{API_PREFIX}{path}", "POST")

    assert route.service == "read-service"


def test_the_delivery_log_beats_the_read_services_broad_prefix():
    """It is the one read answered by a service that owns its own Postgres, so
    a prefix route would send it to a projection that has no such table."""

    route = resolve(f"{API_PREFIX}/webhooks/abc/deliveries", "GET")

    assert route.service == "webhook-service"
    assert route.is_regex, "a prefix route cannot out-specify /api/v1 for this path"


@pytest.mark.parametrize("endpoint", GO_ROUTES + WEBSOCKET_ROUTES, ids=str)
def test_the_routes_without_a_schema_are_still_pinned(endpoint):
    """These are named by hand in `surface.py` because their services publish no
    OpenAPI document. Resolving them against kong.yml is what stops that list
    from drifting into fiction."""

    assert resolve(_concrete(endpoint.path), endpoint.method) is not None


def test_the_stream_and_the_socket_reach_the_services_that_hold_them_open():
    assert resolve(f"{API_PREFIX}/notifications/stream", "GET").service == "push-service"
    assert resolve(f"{API_PREFIX}/chat/advice", "GET").service == "ai-service"


def test_a_long_lived_connection_is_not_cut_off_by_a_proxy_timeout():
    """A ten-second read timeout would end an idle SSE stream or socket that is
    behaving exactly as designed."""

    import yaml

    from ..documents import KONG_CONFIG

    config = yaml.safe_load(KONG_CONFIG.read_text())
    for name in ("push-service", "ai-service"):
        service = next(entry for entry in config["services"] if entry["name"] == name)

        assert service["read_timeout"] >= 3_600_000, f"{name} would time out a live stream"


def test_no_route_still_carries_the_retired_reads_alias():
    """Read-service used to serve `/api/v1/reads/*`. Step 0.5 moved the split
    into the gateway; nothing should reintroduce the segment."""

    for route in routes():
        assert "/reads" not in route.path or "fallback-reads" in route.path


def test_the_read_service_serves_no_reads_prefixed_path():
    for path in schema_of("read-service").document["paths"]:
        assert not path.startswith(f"{API_PREFIX}/reads")
