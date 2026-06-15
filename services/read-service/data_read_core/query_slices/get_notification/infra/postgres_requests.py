from data_read_core.shared.postgres_orm import NotificationReadModel


async def fetch_owned_notification(
    user_id: int,
    notification_id: str,
) -> NotificationReadModel | None:
    return await NotificationReadModel.objects.filter(
        id=notification_id,
        user_id=user_id,
    ).afirst()
