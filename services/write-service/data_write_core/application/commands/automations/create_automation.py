from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from data_write_core.domain.automations import (
    validate_effects,
    validate_trigger,
)
from data_write_core.domain.entities import AutomationEntity

from ...dtos import AutomationDTO, automation_to_dto
from ._base_handler import AutomationCommandHandler
from ._events import automation_created
from ._utilities import effects_from, trigger_from


@dataclass(frozen=True)
class CreateAutomationCommand:
    user_id: int
    user_external_id: str
    name: str
    trigger: dict[str, Any]
    effects: list[dict[str, Any]]
    icon: str = ""
    enabled: bool = True


class CreateAutomationCommandHandler(AutomationCommandHandler):
    async def handle(self, command: CreateAutomationCommand) -> tuple[AutomationDTO, int]:
        validate_trigger(command.trigger)
        validate_effects(command.effects, command.trigger["type"])

        holder: dict[str, AutomationEntity] = {}
        automation = AutomationEntity(
            id=str(uuid4()),
            user_id=str(command.user_id),
            user_external_id=command.user_external_id,
            name=command.name,
            icon=command.icon,
            enabled=command.enabled,
            trigger=trigger_from(command.trigger),
            effects=effects_from(command.effects),
            created_at=datetime.now(UTC),
        )

        async def write() -> None:
            holder["automation"] = await self._automation_repository.create_automation(automation)

        async def undo() -> None:
            await self._automation_repository.hard_delete_automation(UUID(automation.unique_id))

        return (
            automation_to_dto(holder.get("automation", automation)),
            await self._run_saga(
                write,
                undo,
                [automation_created(automation)],
            ),
        )
