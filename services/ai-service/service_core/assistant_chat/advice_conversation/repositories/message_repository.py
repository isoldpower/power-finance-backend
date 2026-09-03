from abc import ABC, abstractmethod
from uuid import UUID

from ..contracts import (
    ConversationMessage,
    MessageStatus,
    ResourceReference,
)


class MessageRepository(ABC):
    @abstractmethod
    async def append(self, external_id: str, message: ConversationMessage) -> None: ...

    @abstractmethod
    async def settle(
        self,
        message_id: UUID,
        status: MessageStatus,
        text: str,
        refs: tuple[ResourceReference, ...],
    ) -> None: ...

    @abstractmethod
    async def page(
        self,
        external_id: str,
        limit: int,
        anchor: tuple | None = None,
        backwards: bool = False,
    ) -> list[ConversationMessage]: ...

    @abstractmethod
    async def count(self, external_id: str) -> int: ...

    @abstractmethod
    async def clear(self, external_id: str) -> int: ...
