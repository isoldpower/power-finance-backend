from django.db.models import Count, Q

from data_read_core.shared.postgres_orm import NotificationReadModel


async def count_notifications(user_id: int) -> tuple[int, int]:
    counted = await NotificationReadModel.objects.filter(user_id=user_id).aaggregate(
        total=Count("id"),
        unacknowledged=Count(
            "id",
            filter=Q(acknowledged_at__isnull=True),
        ),
    )

    return (
        counted["unacknowledged"] or 0,
        counted["total"] or 0,
    )
