from collections.abc import Awaitable, Callable

from asgiref.sync import iscoroutinefunction, markcoroutinefunction
from django.http import HttpRequest, HttpResponse

from .context_propagator import (
    AsyncContextPropagator,
    ContextPropagator,
    SyncContextPropagator,
)
from .utilities import resolve_header_name


class CorrelationIDMiddleware:
    """Read the correlation-ID header from inbound requests (set by the API
    Gateway per the CQRS spec) or generate a fresh UUID4 if absent. The
    value is stashed in a ContextVar so logging, Kafka producers, and DB
    query comments can read it via `correlation.get_correlation_id()`.
    Echoed back on the response so callers can correlate client- and
    server-side traces.

    The header name is read once at middleware initialization from
    `settings.CORRELATION_ID_HEADER` (which each service loads from its own
    `.env`), falling back to `X-Correlation-ID`. Reading at init keeps the
    per-request hot path free of settings lookups.

    Picks a sync or async propagator strategy at construction time based on
    the inner `get_response`, so the middleware works under both WSGI and
    ASGI stacks without per-request dispatch overhead.
    """

    sync_capable: bool = True
    async_capable: bool = True
    _propagator: ContextPropagator

    def __init__(
        self,
        get_response: Callable[[HttpRequest], HttpResponse | Awaitable[HttpResponse]],
    ) -> None:
        header_name = resolve_header_name()
        if iscoroutinefunction(get_response):
            self._propagator = AsyncContextPropagator(get_response, header_name)
            markcoroutinefunction(self)
        else:
            self._propagator = SyncContextPropagator(get_response, header_name)

    def __call__(self, request: HttpRequest):
        return self._propagator(request)
