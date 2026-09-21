from data_read_core.shared.pagination import PageRequest, apply_keyset
from data_read_core.shared.postgres_orm import NotificationReadModel

from ..dtos import NotificationFilters


def _owned_queryset(user_id: int, filters: NotificationFilters):
    queryset = NotificationReadModel.objects.filter(user_id=user_id)
    if filters.acknowledged is not None:
        queryset = queryset.filter(
            acknowledged_at__isnull=not filters.acknowledged,
        )
    if filters.severity is not None:
        queryset = queryset.filter(
            severity=filters.severity,
        )

    return queryset


async def fetch_owned_notifications(
    user_id: int,
    page: PageRequest,
    filters: NotificationFilters,
) -> list[NotificationReadModel]:
    queryset = apply_keyset(
        _owned_queryset(user_id, filters),
        page,
    )

    return [notification async for notification in queryset]


async def count_owned_notifications(user_id: int, filters: NotificationFilters) -> int:
    return await _owned_queryset(user_id, filters).acount()
