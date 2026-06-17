from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from typing import Generic, TypeVar

from django.http import HttpRequest, HttpResponse

TResponse = TypeVar("TResponse", HttpResponse, Awaitable[HttpResponse])


class ContextPropagator(ABC, Generic[TResponse]):
    def __init__(
        self,
        get_response: Callable[[HttpRequest], TResponse],
        header_name: str,
    ) -> None:
        self.get_response: Callable[[HttpRequest], TResponse] = get_response
        self.header_name = header_name

    @abstractmethod
    def __call__(self, request: HttpRequest):
        raise NotImplementedError()
