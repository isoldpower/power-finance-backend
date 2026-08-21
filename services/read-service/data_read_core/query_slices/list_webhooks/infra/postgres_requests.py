from data_read_core.shared.pagination import PageRequest, apply_keyset
from data_read_core.shared.postgres_orm import WebhookReadModel


def _owned_queryset(user_id: int):
    return WebhookReadModel.objects.filter(user_id=user_id)


async def fetch_owned_webhooks(
    user_id: int,
    page: PageRequest,
) -> list[WebhookReadModel]:
    """One page plus the lookahead row `build_page` needs to mint cursors."""

    queryset = apply_keyset(_owned_queryset(user_id), page)

    return [webhook async for webhook in queryset]


async def count_owned_webhooks(user_id: int) -> int:
    return await _owned_queryset(user_id).acount()
