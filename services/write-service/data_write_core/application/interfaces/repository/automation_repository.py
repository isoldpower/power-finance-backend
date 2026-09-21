from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID

from write_service.common.pagination import PageRequest

from data_write_core.domain.entities import AutomationEntity


class AutomationRepository(ABC):
    @abstractmethod
    async def create_automation(self, automation: AutomationEntity) -> AutomationEntity:
        raise NotImplementedError()

    @abstractmethod
    async def save_automation(self, automation: AutomationEntity) -> AutomationEntity:
        raise NotImplementedError()

    @abstractmethod
    async def list_user_automations(
        self,
        user_id: int,
        page: PageRequest,
        enabled: bool | None,
    ) -> list[AutomationEntity]:
        raise NotImplementedError()

    @abstractmethod
    async def count_user_automations(
        self,
        user_id: int,
        enabled: bool | None,
    ) -> int:
        raise NotImplementedError()

    @abstractmethod
    async def get_user_automation_by_id(
        self,
        automation_id: UUID,
        user_id: int,
    ) -> AutomationEntity:
        raise NotImplementedError()

    @abstractmethod
    async def hard_delete_automation(self, automation_id: UUID) -> None:
        raise NotImplementedError()

    @abstractmethod
    async def list_live_for_event(self, user_id: int, event: str) -> list[AutomationEntity]:
        raise NotImplementedError()

    @abstractmethod
    async def list_live_scheduled(self, schedule: str) -> list[AutomationEntity]:
        raise NotImplementedError()

    @abstractmethod
    async def claim_run(
        self,
        automation_id: UUID,
        user_id: int,
        run_key: str,
        at: datetime,
    ) -> bool:
        raise NotImplementedError()

    @abstractmethod
    async def record_run(self, automation_id: UUID, at: datetime) -> int:
        raise NotImplementedError()
