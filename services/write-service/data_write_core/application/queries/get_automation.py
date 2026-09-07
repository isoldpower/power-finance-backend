from dataclasses import dataclass
from uuid import UUID

from ..bootstrap import get_repository_registry
from ..dtos import AutomationDTO, automation_to_dto
from ..interfaces import AutomationRepository


@dataclass(frozen=True)
class GetFallbackAutomationQuery:
    user_id: int
    automation_id: UUID


class GetFallbackAutomationQueryHandler:
    def __init__(self, automation_repository: AutomationRepository | None = None) -> None:
        self._automation_repository = (
            automation_repository or get_repository_registry().automation_repository
        )

    async def handle(self, query: GetFallbackAutomationQuery) -> AutomationDTO:
        found = await self._automation_repository.get_user_automation_by_id(
            automation_id=query.automation_id,
            user_id=query.user_id,
        )

        return automation_to_dto(found)
