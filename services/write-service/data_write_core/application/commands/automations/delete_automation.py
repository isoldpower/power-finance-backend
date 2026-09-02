from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from data_write_core.domain.entities import AutomationEntity

from ...dtos import AutomationDTO, automation_to_dto
from ._base_handler import AutomationCommandHandler
from ._events import automation_deleted


@dataclass(frozen=True)
class DeleteAutomationCommand:
    user_id: int
    user_external_id: str
    automation_id: UUID


class DeleteAutomationCommandHandler(AutomationCommandHandler):
    async def handle(self, command: DeleteAutomationCommand) -> tuple[AutomationDTO, int]:
        automation = await self._automation_repository.get_user_automation_by_id(
            command.automation_id,
            command.user_id,
        )

        before = automation.snapshot()
        deleted_at = datetime.now(UTC)
        automation.soft_delete(deleted_at)
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
                [automation_deleted(automation, deleted_at)],
            ),
        )
