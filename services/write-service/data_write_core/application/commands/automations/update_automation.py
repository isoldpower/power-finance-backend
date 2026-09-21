from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from data_write_core.domain.automations import (
    validate_effects,
    validate_trigger,
)
from data_write_core.domain.entities import AutomationEntity

from ...dtos import AutomationDTO, automation_to_dto
from ._base_handler import AutomationCommandHandler
from ._events import automation_updated
from ._utilities import effects_from, trigger_from


@dataclass(frozen=True)
class UpdateAutomationCommand:
    user_id: int
    user_external_id: str
    automation_id: UUID
    name: str | None = None
    icon: str | None = None
    enabled: bool | None = None
    trigger: dict[str, Any] | None = None
    effects: list[dict[str, Any]] | None = None


class UpdateAutomationCommandHandler(AutomationCommandHandler):
    async def handle(self, command: UpdateAutomationCommand) -> tuple[AutomationDTO, int]:
        automation = await self._automation_repository.get_user_automation_by_id(
            command.automation_id,
            command.user_id,
        )

        before = automation.snapshot()
        if command.trigger is not None:
            validate_trigger(command.trigger)
            automation.replace_trigger(trigger_from(command.trigger))
        if command.effects is not None:
            validate_effects(command.effects, automation.trigger.type)
            automation.replace_effects(effects_from(command.effects))

        automation.rename(command.name, command.icon)
        if command.enabled is not None:
            automation.set_enabled(command.enabled)

        updated_at = datetime.now(UTC)
        automation.touch(updated_at)
        holder: dict[str, AutomationEntity] = {}

        async def write() -> None:
            holder["automation"] = await self._automation_repository.save_automation(automation)

        async def undo() -> None:
            automation.restore(before)
            await self._automation_repository.save_automation(automation)

        return (
            automation_to_dto(holder.get("automation", automation)),
            await self._run_saga(
                write,
                undo,
                [automation_updated(automation, updated_at)],
            ),
        )
