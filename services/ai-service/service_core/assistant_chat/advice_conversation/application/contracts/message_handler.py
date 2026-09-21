from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from .connection_context import ConnectionContext


class MessageHandler(ABC):
    @abstractmethod
    def handle(self, message: dict, context: ConnectionContext) -> AsyncIterator[dict]: ...

    async def is_responsible(self, message: dict, context: ConnectionContext) -> bool:
        return True

    async def is_singleton(self, message: dict, context: ConnectionContext) -> bool:
        return True
