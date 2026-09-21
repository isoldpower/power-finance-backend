from data_read_core.shared.pagination import PageRequest, apply_keyset
from data_read_core.shared.postgres_orm import ActionReadModel

from ..dtos import ActionFilters


def _owned_queryset(user_id: int, filters: ActionFilters):
    queryset = ActionReadModel.objects.filter(
        user_id=user_id,
        status=filters.status,
    )
    if filters.source is not None:
        queryset = queryset.filter(
            source=filters.source,
        )
    if filters.severity is not None:
        queryset = queryset.filter(
            severity=filters.severity,
        )

    return queryset


async def fetch_owned_actions(
    user_id: int,
    page: PageRequest,
    filters: ActionFilters,
) -> list[ActionReadModel]:
    queryset = apply_keyset(
        _owned_queryset(user_id, filters),
        page,
    )

    return [action async for action in queryset]


async def count_owned_actions(user_id: int, filters: ActionFilters) -> int:
    return await _owned_queryset(user_id, filters).acount()
