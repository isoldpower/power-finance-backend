from abc import ABC, abstractmethod

from ..dtos import ConversationActivityDTO


class ActivitySource(ABC):
    @abstractmethod
    async def read(self, external_id: str) -> ConversationActivityDTO: ...
