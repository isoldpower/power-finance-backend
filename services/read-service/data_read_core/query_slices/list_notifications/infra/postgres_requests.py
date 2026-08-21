from data_read_core.shared.pagination import PageRequest, apply_keyset
from data_read_core.shared.postgres_orm import NotificationReadModel


def _owned_queryset(user_id: int, only_unread: bool):
    queryset = NotificationReadModel.objects.filter(user_id=user_id)
    if only_unread:
        queryset = queryset.filter(is_read=False)

    return queryset


async def fetch_owned_notifications(
    user_id: int,
    page: PageRequest,
    only_unread: bool = False,
) -> list[NotificationReadModel]:
    """One page plus the lookahead row `build_page` needs to mint cursors."""

    queryset = apply_keyset(
        _owned_queryset(user_id, only_unread),
        page,
    )

    return [notification async for notification in queryset]


async def count_owned_notifications(user_id: int, only_unread: bool = False) -> int:
    return await _owned_queryset(user_id, only_unread).acount()
