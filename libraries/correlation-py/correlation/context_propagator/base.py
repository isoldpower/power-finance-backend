from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable

from django.http import HttpRequest, HttpResponse


class ContextPropagator(ABC):
    """Strategy for wrapping a Django `get_response` callable with the
    correlation-ID lifecycle: read/generate the ID from the request, attach
    it to the ContextVar, invoke the inner chain, reset the ContextVar,
    and echo the ID on the response.

    Concrete subclasses (`SyncContextPropagator`, `AsyncContextPropagator`)
    differ only in how they dispatch the inner call. The HTTP header name is
    injected by the middleware (which reads it from Django settings at
    init) so the lib itself stays config-free.
    """

    def __init__(
        self,
        get_response: Callable[[HttpRequest], HttpResponse | Awaitable[HttpResponse]],
        header_name: str,
    ) -> None:
        self.get_response = get_response
        self.header_name = header_name

    @abstractmethod
    def __call__(self, request: HttpRequest):
        raise NotImplementedError()
