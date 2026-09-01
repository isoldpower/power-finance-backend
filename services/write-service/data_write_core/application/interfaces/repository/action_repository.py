from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID

from data_write_core.domain.entities import ActionEntity


class ActionRepository(ABC):
    @abstractmethod
    async def create_action(
        self,
        action: ActionEntity,
    ) -> ActionEntity:
        raise NotImplementedError()

    @abstractmethod
    async def save_action(
        self,
        action: ActionEntity,
    ) -> ActionEntity:
        raise NotImplementedError()

    @abstractmethod
    async def get_user_action_by_id(self, action_id: UUID, user_id: int) -> ActionEntity:
        raise NotImplementedError()

    @abstractmethod
    async def find_pending_by_group_key(
        self,
        user_id: int,
        group_key: str,
    ) -> ActionEntity | None:
        raise NotImplementedError()

    @abstractmethod
    async def hard_delete_action(
        self,
        action_id: UUID,
    ) -> None:
        raise NotImplementedError()

    @abstractmethod
    async def find_lapsed_pending(
        self,
        now: datetime,
        limit: int,
    ) -> list[ActionEntity]:
        raise NotImplementedError()
