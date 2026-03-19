from typing import Any

from finances.application.dtos import WebhookDTO


class WebhookHttpPresenter:
    @staticmethod
    def present_one_with_secret(webhook: WebhookDTO) -> dict[str, Any]:
        return {
            "id": webhook.id,
            "url": webhook.url,
            "title": webhook.title,
            "secret": webhook.secret,
            "subscribed": webhook.subscribed_events,
            "meta": WebhookHttpPresenter.present_meta(webhook)
        }

    @staticmethod
    def present_one(webhook: WebhookDTO) -> dict[str, Any]:
        return {
            "id": webhook.id,
            "url": webhook.url,
            "title": webhook.title,
            "subscribed": webhook.subscribed_events,
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
            "subscribed": webhook.subscribed_events,
        } for webhook in webhooks]