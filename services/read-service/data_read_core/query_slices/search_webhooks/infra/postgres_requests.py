from django.db.models import Q

from data_read_core.shared.postgres_orm import WebhookReadModel


async def search_owned_webhooks(
    user_id: int,
    filter_query: Q,
    limit: int,
    offset: int,
) -> tuple[list[WebhookReadModel], int]:
    queryset = WebhookReadModel.objects.filter(filter_query, user_id=user_id)
    total = await queryset.acount()
    page = queryset.order_by("-created_at")[offset : offset + limit]

    return [webhook async for webhook in page], total
