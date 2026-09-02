from datetime import datetime
from uuid import UUID

from django.db import IntegrityError
from django.db.models import F

from data_write_core.application.interfaces import AutomationRepository
from data_write_core.domain.entities import AutomationEntity

from ..orm import AutomationModel, AutomationRunModel
from .mappers import AutomationMapper


class DjangoAutomationRepository(AutomationRepository):
    async def create_automation(self, automation: AutomationEntity) -> AutomationEntity:
        created = AutomationModel()
        AutomationMapper.apply_to_model(created, automation)
        await created.asave()

        return AutomationMapper.to_domain(await AutomationModel.objects.aget(id=created.id))

    async def save_automation(self, automation: AutomationEntity) -> AutomationEntity:
        stored = await AutomationModel.objects.aget(id=automation.unique_id)
        AutomationMapper.apply_to_model(stored, automation)
        await stored.asave()

        return AutomationMapper.to_domain(stored)

    async def get_user_automation_by_id(
        self,
        automation_id: UUID,
        user_id: int,
    ) -> AutomationEntity:
        found = await AutomationModel.objects.aget(
            id=automation_id,
            user_id=user_id,
        )

        return AutomationMapper.to_domain(found)

    async def hard_delete_automation(self, automation_id: UUID) -> None:
        await AutomationModel.objects.filter(id=automation_id).adelete()

    async def list_live_for_event(self, user_id: int, event: str) -> list[AutomationEntity]:
        queryset = AutomationModel.objects.filter(
            user_id=user_id,
            enabled=True,
            deleted_at__isnull=True,
            trigger_type="event",
            trigger_event=event,
        ).order_by("created_at", "id")

        return [AutomationMapper.to_domain(row) async for row in queryset]

    async def list_live_scheduled(self, schedule: str) -> list[AutomationEntity]:
        queryset = AutomationModel.objects.filter(
            enabled=True,
            deleted_at__isnull=True,
            trigger_type="schedule",
            trigger_schedule=schedule,
        ).order_by("created_at", "id")

        return [AutomationMapper.to_domain(row) async for row in queryset]

    async def claim_run(
        self,
        automation_id: UUID,
        user_id: int,
        run_key: str,
        at: datetime,
    ) -> bool:
        try:
            await AutomationRunModel.objects.acreate(
                automation_id=automation_id,
                user_id=user_id,
                run_key=run_key,
                ran_at=at,
            )
        except IntegrityError:
            return False

        return True

    async def record_run(self, automation_id: UUID, at: datetime) -> int:
        await AutomationModel.objects.filter(id=automation_id).aupdate(
            runs=F("runs") + 1,
            last_run_at=at,
        )
        counted = await AutomationModel.objects.filter(id=automation_id).afirst()

        return counted.runs if counted else 0
