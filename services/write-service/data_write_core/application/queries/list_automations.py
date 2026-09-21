import asyncio
from dataclasses import dataclass

from write_service.common.pagination import PageRequest

from ..bootstrap import get_repository_registry
from ..dtos import AutomationDTO, automation_to_dto
from ..interfaces import AutomationRepository
from ..query_filters import FallbackAutomationFilters


@dataclass(frozen=True)
class ListFallbackAutomationsQuery:
    user_id: int
    page: PageRequest
    filters: FallbackAutomationFilters


class ListFallbackAutomationsQueryHandler:
    def __init__(self, automation_repository: AutomationRepository | None = None) -> None:
        self._automation_repository = (
            automation_repository or get_repository_registry().automation_repository
        )

    async def handle(self, query: ListFallbackAutomationsQuery) -> tuple[list[AutomationDTO], int]:
        automations, total = await asyncio.gather(
            self._automation_repository.list_user_automations(
                user_id=query.user_id,
                page=query.page,
                enabled=query.filters.enabled,
            ),
            self._automation_repository.count_user_automations(
                user_id=query.user_id,
                enabled=query.filters.enabled,
            ),
        )

        return [automation_to_dto(automation) for automation in automations], total
