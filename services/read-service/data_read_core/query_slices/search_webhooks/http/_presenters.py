from ..dtos import WebhookDTO


def present_one(webhook: WebhookDTO) -> dict:
    return {
        "id": webhook.id,
        "title": webhook.title,
        "url": webhook.url,
        "is_active": webhook.is_active,
        "created_at": webhook.created_at,
        "updated_at": webhook.updated_at,
        "deleted_at": None,
    }


def present_many(webhooks: list[WebhookDTO]) -> list[dict]:
    return [present_one(webhook) for webhook in webhooks]
