from abc import ABC, abstractmethod

from .connection_context import ConnectionContext


class MessageHandler(ABC):
    @abstractmethod
    async def handle(self, message: dict, context: ConnectionContext) -> str | None:
        """How do we handle this message?"""

        ...

    async def is_responsible(self, message: dict, context: ConnectionContext) -> bool:
        """Is the handler responsible for this message (used for on-flight determination)?"""

        return True

    async def is_singleton(self, message: dict, context: ConnectionContext) -> bool:
        """Should the handler prevent message from propagating further?"""

        return True
