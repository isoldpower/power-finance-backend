import uuid
from typing import cast

from django.http import HttpRequest, HttpResponse

from ..utilities import attach_correlation_id, reset_correlation_id
from .base import ContextPropagator


class SyncContextPropagator(ContextPropagator):
    def __call__(self, request: HttpRequest) -> HttpResponse:
        correlation_id = request.headers.get(self.header_name) or str(uuid.uuid4())
        request.correlation_id = correlation_id
        token = attach_correlation_id(correlation_id)

        try:
            response = cast(HttpResponse, self.get_response(request))
        finally:
            reset_correlation_id(token)

        response[self.header_name] = correlation_id
        return response
