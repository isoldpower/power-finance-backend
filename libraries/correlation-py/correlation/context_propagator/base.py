from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from typing import Generic, TypeVar

from django.http import HttpRequest, HttpResponse

from ..request_scope import RequestScopeBinder, RequestScopeBinding

TResponse = TypeVar("TResponse", HttpResponse, Awaitable[HttpResponse])


class ContextPropagator(ABC, Generic[TResponse]):
    def __init__(
        self,
        get_response: Callable[[HttpRequest], TResponse],
        header_name: str,
    ) -> None:
        self.get_response: Callable[[HttpRequest], TResponse] = get_response
        self.header_name = header_name
        self.request_scope_binder = RequestScopeBinder(correlation_header_name=header_name)

    @abstractmethod
    def __call__(self, request: HttpRequest):
        raise NotImplementedError()

    def _bind_request_scope(self, request: HttpRequest) -> RequestScopeBinding:
        binding = self.request_scope_binder.bind(request)
        request.correlation_id = binding.correlation_id
        request.sandbox_id = binding.sandbox_id

        return binding

    def _unbind_request_scope(self, binding: RequestScopeBinding) -> None:
        self.request_scope_binder.unbind(binding)

    def _stamp_response(self, response: HttpResponse, binding: RequestScopeBinding) -> None:
        response[self.header_name] = binding.correlation_id
