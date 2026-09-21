from ..dtos import WebhookDTO


def present_one(webhook: WebhookDTO) -> dict:
    return {
        "id": webhook.id,
        "title": webhook.title,
        "url": webhook.url,
        "enabled": webhook.is_active,
        "created_at": webhook.created_at,
        "updated_at": webhook.updated_at,
    }
