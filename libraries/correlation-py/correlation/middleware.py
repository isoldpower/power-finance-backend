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
