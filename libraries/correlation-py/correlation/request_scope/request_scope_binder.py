from typing import NamedTuple

from django.http import HttpRequest

from ..utilities import resolve_header_name, resolve_sandbox_header_name
from .correlation_binding import CorrelationBinder, CorrelationBinding
from .sandbox_binding import SandboxBinder, SandboxBinding


class RequestScopeBinding(NamedTuple):
    correlation: CorrelationBinding
    sandbox: SandboxBinding

    @property
    def correlation_id(self) -> str:
        return self.correlation.correlation_id

    @property
    def sandbox_id(self) -> str | None:
        return self.sandbox.sandbox_id


class RequestScopeBinder:
    def __init__(
        self,
        correlation_header_name: str | None = None,
        sandbox_header_name: str | None = None,
    ) -> None:
        self._correlation_binder = CorrelationBinder(
            correlation_header_name or resolve_header_name(),
        )
        self._sandbox_binder = SandboxBinder(
            sandbox_header_name or resolve_sandbox_header_name(),
        )

    def bind(self, request: HttpRequest) -> RequestScopeBinding:
        sandbox_binding = self._sandbox_binder.bind(request)
        correlation_binding = self._correlation_binder.bind(request)

        return RequestScopeBinding(
            correlation=correlation_binding,
            sandbox=sandbox_binding,
        )

    def unbind(self, binding: RequestScopeBinding) -> None:
        self._correlation_binder.unbind(binding.correlation)
        self._sandbox_binder.unbind(binding.sandbox)
