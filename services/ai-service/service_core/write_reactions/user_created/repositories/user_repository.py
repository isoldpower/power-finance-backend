from abc import ABC, abstractmethod
from datetime import datetime


class UserRepository(ABC):
    @abstractmethod
    async def remember(
        self,
        user_id: int,
        external_id: str,
        now: datetime,
    ) -> None:
        raise NotImplementedError()
