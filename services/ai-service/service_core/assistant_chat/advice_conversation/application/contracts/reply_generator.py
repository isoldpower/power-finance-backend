from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from .connection_context import ConnectionContext


class ReplyGenerator(ABC):
    @abstractmethod
    def generate(self, prompt: str, context: ConnectionContext) -> AsyncIterator[str]: ...
