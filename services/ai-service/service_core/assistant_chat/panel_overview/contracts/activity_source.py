from abc import ABC, abstractmethod

from .activity import ConversationActivity


class ActivitySource(ABC):
    @abstractmethod
    async def read(self, external_id: str) -> ConversationActivity: ...
