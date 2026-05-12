from typing import Any

from finances.application.dtos import WebhookDTO, WebhookSubscriptionDTO


class WebhookHttpPresenter:
    @staticmethod
    def present_one_with_secret(webhook: WebhookDTO) -> dict[str, Any]:
        return {
            "id": webhook.id,
            "url": webhook.url,
            "title": webhook.title,
            "secret": webhook.secret,
            "meta": WebhookHttpPresenter.present_meta(webhook)
        }

    @staticmethod
    def present_one(webhook: WebhookDTO) -> dict[str, Any]:
        return {
            "id": webhook.id,
            "url": webhook.url,
            "title": webhook.title,
            "meta": WebhookHttpPresenter.present_meta(webhook)
        }

    @staticmethod
    def present_meta(webhook: WebhookDTO) -> dict[str, Any]:
        return {
            "id": webhook.id,
            "created_at": webhook.created_at,
            "updated_at": webhook.updated_at,
        }

    @staticmethod
    def present_many(webhooks: list[WebhookDTO]) -> list[dict[str, Any]]:
        return [{
            "id": webhook.id,
            "url": webhook.url,
            "title": webhook.title,
        } for webhook in webhooks]

    @staticmethod
    def present_subscription(subscription: WebhookSubscriptionDTO) -> dict[str, Any]:
        return {
            "id": subscription.id,
            "event_type": subscription.event_type,
            "is_active": subscription.is_active
        }

    @staticmethod
    def present_subscription_list(subscriptions: list[WebhookSubscriptionDTO]) -> list[dict[str, Any]]:
        return [{
            "id": subscription.id,
            "event_type": subscription.event_type,
            "is_active": subscription.is_active
        } for subscription in subscriptions]