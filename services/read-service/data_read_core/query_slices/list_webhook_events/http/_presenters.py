from ..dtos import WebhookSubscriptionDTO


def present_one(subscription: WebhookSubscriptionDTO) -> dict:
    return {
        "id": subscription.id,
        "webhook_id": subscription.webhook_id,
        "event": subscription.event_type,
        "created_at": subscription.created_at,
    }


def present_many(subscriptions: list[WebhookSubscriptionDTO]) -> list[dict]:
    return [present_one(subscription) for subscription in subscriptions]
