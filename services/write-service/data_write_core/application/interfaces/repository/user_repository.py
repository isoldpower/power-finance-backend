from abc import ABC, abstractmethod

from data_write_core.domain.entities import InternalUserEntity


class UserRepository(ABC):
    @abstractmethod
    async def get_synced_internal(self, external_id: str) -> InternalUserEntity:
        raise NotImplementedError()
