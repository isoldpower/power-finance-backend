from data_read_core.shared.postgres_orm import WebhookReadModel


async def fetch_owned_webhooks(
    user_id: int,
    limit: int,
    offset: int,
) -> list[WebhookReadModel]:
    queryset = WebhookReadModel.objects.filter(user_id=user_id).order_by("-created_at")[
        offset : offset + limit
    ]

    return [webhook async for webhook in queryset]


async def count_owned_webhooks(user_id: int) -> int:
    return await WebhookReadModel.objects.filter(user_id=user_id).acount()
