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
            "is_active": webhook.is_active,
            "created_at": to_iso(webhook.created_at),
            "updated_at": to_iso(webhook.updated_at),
            # Always present, null when unset.
            "deleted_at": None,
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
            "event_type": subscription.event_type,
            "is_active": subscription.is_active,
            "created_at": to_iso(subscription.created_at),
            "updated_at": None,
            "deleted_at": None,
        }

    @staticmethod
    def present_subscriptions(subscriptions: list[WebhookSubscriptionDTO]) -> list[dict]:
        return [
            WebhookHttpPresenter.present_subscription(subscription)
            for subscription in subscriptions
        ]
