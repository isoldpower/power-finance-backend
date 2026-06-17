from data_read_core.shared.postgres_orm import WebhookReadModel


async def fetch_owned_webhook(user_id: int, webhook_id: str) -> WebhookReadModel | None:
    return await WebhookReadModel.objects.filter(
        id=webhook_id,
        user_id=user_id,
    ).afirst()
