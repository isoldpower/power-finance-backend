from data_read_core.shared.pagination import PageRequest, apply_keyset
from data_read_core.shared.postgres_orm import WebhookReadModel

from ..dtos import WebhookFilters


def _owned_queryset(user_id: int, filters: WebhookFilters):
    queryset = WebhookReadModel.objects.filter(user_id=user_id)
    if filters.enabled is not None:
        queryset = queryset.filter(is_active=filters.enabled)

    return queryset


async def fetch_owned_webhooks(
    user_id: int,
    page: PageRequest,
    filters: WebhookFilters,
) -> list[WebhookReadModel]:
    """One page plus the lookahead row `build_page` needs to mint cursors."""

    queryset = apply_keyset(_owned_queryset(user_id, filters), page)

    return [webhook async for webhook in queryset]


async def count_owned_webhooks(user_id: int, filters: WebhookFilters) -> int:
    return await _owned_queryset(user_id, filters).acount()
