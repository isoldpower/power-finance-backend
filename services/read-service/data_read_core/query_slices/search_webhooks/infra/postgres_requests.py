from django.db.models import Q

from data_read_core.shared.pagination import PageRequest, apply_keyset
from data_read_core.shared.postgres_orm import WebhookReadModel


async def search_owned_webhooks(
    user_id: int,
    filter_query: Q,
    page: PageRequest,
) -> tuple[list[WebhookReadModel], int]:
    queryset = WebhookReadModel.objects.filter(filter_query, user_id=user_id)
    total = await queryset.acount()
    rows = apply_keyset(queryset, page)

    return [webhook async for webhook in rows], total
