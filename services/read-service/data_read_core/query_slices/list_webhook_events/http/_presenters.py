from ..dtos import WebhookSubscriptionDTO


def present_one(subscription: WebhookSubscriptionDTO) -> dict:
    return {
        "id": subscription.id,
        "webhook_id": subscription.webhook_id,
        "event_type": subscription.event_type,
        "is_active": subscription.is_active,
        "created_at": subscription.created_at,
        "updated_at": None,
        "deleted_at": None,
    }


def present_many(subscriptions: list[WebhookSubscriptionDTO]) -> list[dict]:
    return [present_one(subscription) for subscription in subscriptions]
