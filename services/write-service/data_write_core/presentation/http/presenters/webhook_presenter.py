from write_service.common.timestamps import to_iso

from data_write_core.application.dtos import (
    WebhookDTO,
    WebhookSubscriptionDTO,
    WebhookWithSecretDTO,
)


class WebhookHttpPresenter:
    @staticmethod
    def present_one(webhook: WebhookDTO) -> dict:
        return {
            "id": str(webhook.id),
            "title": webhook.title,
            "url": webhook.url,
            "enabled": webhook.enabled,
            "created_at": to_iso(webhook.created_at),
            "updated_at": to_iso(webhook.updated_at),
        }

    @staticmethod
    def present_many(webhooks: list[WebhookDTO]) -> list[dict]:
        return [WebhookHttpPresenter.present_one(webhook) for webhook in webhooks]

    @staticmethod
    def present_with_secret(webhook: WebhookWithSecretDTO) -> dict:
        payload = WebhookHttpPresenter.present_one(webhook)
        payload["secret"] = webhook.secret

        return payload

    @staticmethod
    def present_subscription(subscription: WebhookSubscriptionDTO) -> dict:
        return {
            "id": str(subscription.id),
            "webhook_id": str(subscription.webhook_id),
            "event": subscription.event_type,
            "created_at": to_iso(subscription.created_at),
        }

    @staticmethod
    def present_subscriptions(subscriptions: list[WebhookSubscriptionDTO]) -> list[dict]:
        return [
            WebhookHttpPresenter.present_subscription(subscription)
            for subscription in subscriptions
        ]
