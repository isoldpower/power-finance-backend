from collections.abc import Awaitable

from django.http import HttpRequest, HttpResponse

from .base import ContextPropagator


class AsyncContextPropagator(ContextPropagator[Awaitable[HttpResponse]]):
    async def __call__(self, request: HttpRequest) -> HttpResponse:
        binding = self._bind_request_scope(request)

        try:
            response = await self.get_response(request)
        finally:
            self._unbind_request_scope(binding)

        self._stamp_response(response, binding)

        return response
