from abc import ABC, abstractmethod


class UserRepository(ABC):
    @abstractmethod
    async def external_id_for(self, user_id: int) -> str | None:
        raise NotImplementedError()
