from data_read_core.shared.postgres_orm import NotificationReadModel


def _owned_queryset(user_id: int, only_unread: bool):
    queryset = NotificationReadModel.objects.filter(user_id=user_id)
    if only_unread:
        queryset = queryset.filter(is_read=False)

    return queryset


async def fetch_owned_notifications(
    user_id: int,
    limit: int,
    offset: int,
    only_unread: bool = False,
) -> list[NotificationReadModel]:
    queryset = _owned_queryset(user_id, only_unread).order_by("-created_at")[
        offset : offset + limit
    ]

    return [notification async for notification in queryset]


async def count_owned_notifications(user_id: int, only_unread: bool = False) -> int:
    return await _owned_queryset(user_id, only_unread).acount()
