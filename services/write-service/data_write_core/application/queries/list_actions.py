import asyncio
from dataclasses import dataclass

from write_service.common.pagination import PageRequest

from data_write_core.application.query_filters import FallbackActionFilters

from ..bootstrap import get_repository_registry
from ..dtos import ActionDTO, action_to_dto
from ..interfaces import ActionRepository


@dataclass(frozen=True)
class ListFallbackActionsQuery:
    user_id: int
    page: PageRequest
    filters: FallbackActionFilters


class ListFallbackActionsQueryHandler:
    def __init__(self, action_repository: ActionRepository | None = None) -> None:
        self._action_repository = action_repository or get_repository_registry().action_repository

    async def handle(self, query: ListFallbackActionsQuery) -> tuple[list[ActionDTO], int]:
        actions, total = await asyncio.gather(
            self._action_repository.list_user_actions(
                user_id=query.user_id,
                page=query.page,
                status=query.filters.status,
                source=query.filters.source,
                severity=query.filters.severity,
            ),
            self._action_repository.count_user_actions(
                user_id=query.user_id,
                status=query.filters.status,
                source=query.filters.source,
                severity=query.filters.severity,
            ),
        )

        return [action_to_dto(action) for action in actions], total
