from abc import ABC, abstractmethod
from uuid import UUID

from ...dtos import ConversationMessageDTO, ResourceReferenceDTO


class MessageRepository(ABC):
    @abstractmethod
    async def append(
        self,
        external_id: str,
        message: ConversationMessageDTO,
    ) -> None: ...

    @abstractmethod
    async def settle(
        self,
        message_id: UUID,
        status: str,
        text: str,
        refs: tuple[ResourceReferenceDTO, ...],
    ) -> None: ...

    @abstractmethod
    async def page(
        self,
        external_id: str,
        limit: int,
        anchor: tuple | None = None,
        backwards: bool = False,
    ) -> list[ConversationMessageDTO]: ...

    @abstractmethod
    async def count(self, external_id: str) -> int: ...

    @abstractmethod
    async def clear(self, external_id: str) -> int: ...
