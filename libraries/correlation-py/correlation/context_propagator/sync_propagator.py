from django.http import HttpRequest, HttpResponse

from .base import ContextPropagator


class SyncContextPropagator(ContextPropagator[HttpResponse]):
    def __call__(self, request: HttpRequest) -> HttpResponse:
        binding = self._bind_request_scope(request)

        try:
            response = self.get_response(request)
        finally:
            self._unbind_request_scope(binding)

        self._stamp_response(response, binding)

        return response
