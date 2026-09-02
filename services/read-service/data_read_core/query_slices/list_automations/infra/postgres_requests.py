from data_read_core.shared.pagination import PageRequest, apply_keyset
from data_read_core.shared.postgres_orm import AutomationReadModel

from ..dtos import AutomationFilters


def _owned_queryset(user_id: int, filters: AutomationFilters):
    queryset = AutomationReadModel.objects.filter(
        user_id=user_id,
        deleted_at__isnull=True,
    )
    if filters.enabled is not None:
        queryset = queryset.filter(enabled=filters.enabled)

    return queryset


async def fetch_owned_automations(
    user_id: int,
    page: PageRequest,
    filters: AutomationFilters,
) -> list[AutomationReadModel]:
    queryset = apply_keyset(_owned_queryset(user_id, filters), page)

    return [automation async for automation in queryset]


async def count_owned_automations(user_id: int, filters: AutomationFilters) -> int:
    return await _owned_queryset(user_id, filters).acount()
