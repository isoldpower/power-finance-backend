from data_read_core.shared.postgres_orm import (
    WebhookReadModel,
    WebhookSubscriptionReadModel,
)


async def webhook_is_owned(user_id: int, webhook_id: str) -> bool:
    return await WebhookReadModel.objects.filter(
        id=webhook_id,
        user_id=user_id,
    ).aexists()


async def fetch_webhook_subscriptions(
    webhook_id: str,
) -> list[WebhookSubscriptionReadModel]:
    queryset = WebhookSubscriptionReadModel.objects.filter(webhook_id=webhook_id).order_by(
        "created_at"
    )

    return [subscription async for subscription in queryset]
