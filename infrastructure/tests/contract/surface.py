"""What the services actually serve.

Read from each service's own generated OpenAPI document rather than from a list
kept here, so a route added anywhere shows up without this suite being edited.
The two Go services publish no schema; their handful of routes is named below
and pinned against the gateway config instead.
"""

import json
import os
import subprocess
from dataclasses import dataclass
from functools import cache

from .documents import METHODS, REPOSITORY, Endpoint

# Enough for `build_app()` to construct a lazy engine; nothing connects.
AI_ENVIRONMENT = {
    "AI_DATABASE_URL": "postgresql+psycopg://unused:unused@127.0.0.1:1/unused",
    "KAFKA_BOOTSTRAP_SERVERS": "127.0.0.1:1",
    "KAFKA_OUTBOX_TOPIC": "events.async",
    "KAFKA_AI_GROUP_ID": "contract-tests",
    "KAFKA_RETRY_TOPIC": "unused.retry",
    "KAFKA_DLQ_TOPIC": "unused.dlq",
    "EXCHANGE_RATES_PROVIDER": "open-er-api",
    "EXCHANGE_RATES_BASE_URL": "http://127.0.0.1:9/unreachable",
}

DJANGO_SCHEMA_COMMAND = (
    "python",
    "manage.py",
    "spectacular",
    "--format",
    "openapi-json",
)

AI_SCHEMA_SCRIPT = (
    "import json;"
    "from ai_service.build_app import build_app;"
    "print(json.dumps(build_app().openapi()))"
)

# Routes belonging to the Go services, which have no OpenAPI document. Each is
# covered by a gateway-routing assertion, so a typo here cannot pass silently.
GO_ROUTES = (
    Endpoint("GET", "/api/v1/notifications/stream"),
    Endpoint("GET", "/api/v1/webhooks/{webhook_id}/deliveries"),
)

# WebSocket upgrades are not OpenAPI operations, so they never appear in a
# generated document however real they are.
WEBSOCKET_ROUTES = (Endpoint("GET", "/api/v1/chat/advice"),)

# Not part of the published API: probes, the schema itself and the internal
# staleness fallback the gateway alone is allowed to call.
INTERNAL_PREFIXES = (
    "/health",
    "/api/schema",
    "/api/docs",
    "/openapi.json",
    "/docs",
    "/redoc",
    "/api/v1/fallback-reads",
)


@dataclass(frozen=True, slots=True)
class ServiceSchema:
    name: str
    document: dict

    @property
    def endpoints(self) -> tuple[Endpoint, ...]:
        found = []
        for path, operations in self.document.get("paths", {}).items():
            for method in operations:
                if method.upper() in METHODS:
                    found.append(Endpoint(method=method.upper(), path=path))

        return tuple(found)


def _run(command: tuple[str, ...], service: str, environment: dict | None = None) -> dict:
    completed = subprocess.run(
        ("uv", "run", *command),
        cwd=REPOSITORY / "services" / service,
        capture_output=True,
        text=True,
        check=True,
        env={**os.environ, **(environment or {})},
    )

    # `manage.py` writes its own log lines to stderr; the document is the last
    # thing on stdout.
    return json.loads(completed.stdout[completed.stdout.index("{") :])


@cache
def schemas() -> tuple[ServiceSchema, ...]:
    return (
        ServiceSchema("read-service", _run(DJANGO_SCHEMA_COMMAND, "read-service")),
        ServiceSchema("write-service", _run(DJANGO_SCHEMA_COMMAND, "write-service")),
        ServiceSchema(
            "ai-service",
            _run(("python", "-c", AI_SCHEMA_SCRIPT), "ai-service", AI_ENVIRONMENT),
        ),
    )


@cache
def schema_of(service: str) -> ServiceSchema:
    return next(schema for schema in schemas() if schema.name == service)


@cache
def documented_endpoints() -> tuple[Endpoint, ...]:
    """Every operation the three OpenAPI documents publish."""

    return tuple(endpoint for schema in schemas() for endpoint in schema.endpoints)


@cache
def public_endpoints() -> tuple[Endpoint, ...]:
    """The surface a client is served, Go routes and sockets included."""

    return tuple(
        [
            endpoint
            for endpoint in documented_endpoints()
            if not endpoint.path.startswith(INTERNAL_PREFIXES)
        ]
        + list(GO_ROUTES)
        + list(WEBSOCKET_ROUTES)
    )
