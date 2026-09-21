from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from ...bootstrap import get_repository_registry
from ...db_utils import aatomic
from ...interfaces import AutomationRepository, OutboxRepository
from ._events import automation_ran


@dataclass(frozen=True)
class RecordAutomationRunCommand:
    user_id: int
    user_external_id: str
    automation_id: UUID
    at: datetime | None = None


class RecordAutomationRunCommandHandler:
    def __init__(
        self,
        automation_repository: AutomationRepository | None = None,
        outbox_repository: OutboxRepository | None = None,
    ) -> None:
        if automation_repository is None or outbox_repository is None:
            registry = get_repository_registry()
            automation_repository = automation_repository or registry.automation_repository
            outbox_repository = outbox_repository or registry.outbox_repository

        self._automation_repository = automation_repository
        self._outbox_repository = outbox_repository

    async def handle(self, command: RecordAutomationRunCommand) -> int:
        ran_at = command.at or datetime.now(UTC)

        async with aatomic():
            counted = await self._automation_repository.record_run(
                command.automation_id,
                ran_at,
            )
            await self._outbox_repository.append(
                automation_ran(
                    automation_id=str(command.automation_id),
                    user_id=command.user_id,
                    user_external_id=command.user_external_id,
                    runs=counted,
                    at=ran_at,
                )
            )

        return counted
