import uuid
from contextvars import Token
from typing import NamedTuple

from django.http import HttpRequest
from observability import current_trace_id_hex

from ..utilities import attach_correlation_id, reset_correlation_id


class CorrelationBinding(NamedTuple):
    correlation_id: str
    attachment_token: Token[str | None]


class CorrelationBinder:
    def __init__(self, correlation_header_name: str) -> None:
        self._correlation_header_name = correlation_header_name

    def bind(self, request: HttpRequest) -> CorrelationBinding:
        correlation_id = self._resolve_correlation_id(request)

        return CorrelationBinding(
            correlation_id=correlation_id,
            attachment_token=attach_correlation_id(correlation_id),
        )

    def unbind(self, binding: CorrelationBinding) -> None:
        reset_correlation_id(binding.attachment_token)

    def _resolve_correlation_id(self, request: HttpRequest) -> str:
        header_correlation_id = request.headers.get(self._correlation_header_name)

        return header_correlation_id or current_trace_id_hex() or str(uuid.uuid4())
