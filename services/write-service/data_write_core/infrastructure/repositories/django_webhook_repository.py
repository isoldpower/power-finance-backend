from uuid import UUID

from data_write_core.application.interfaces import WebhookRepository
from data_write_core.domain.entities import WebhookEntity, WebhookSubscriptionEntity

from ..orm import WebhookModel, WebhookSubscriptionModel
from .mappers import WebhookMapper, WebhookSubscriptionMapper


class DjangoWebhookRepository(WebhookRepository):
    async def create_webhook(self, webhook: WebhookEntity) -> WebhookEntity:
        created_webhook = WebhookModel()
        WebhookMapper.apply_to_model(created_webhook, webhook)
        await created_webhook.asave()

        refreshed = await WebhookModel.objects.aget(id=created_webhook.id)
        return WebhookMapper.to_domain(refreshed)

    async def get_user_webhook_by_id(self, webhook_id: UUID, user_id: int) -> WebhookEntity:
        requested_webhook: WebhookModel = await WebhookModel.objects.aget(
            id=webhook_id,
            user_id=user_id,
        )

        return WebhookMapper.to_domain(requested_webhook)

    async def get_user_webhooks(
        self,
        user_id: int,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[WebhookEntity]:
        queryset = WebhookModel.objects.filter(user_id=user_id).order_by("-created_at")

        start = offset or 0
        if limit is not None:
            queryset = queryset[start : start + limit]
        elif offset is not None:
            queryset = queryset[start:]

        return [WebhookMapper.to_domain(webhook) async for webhook in queryset]

    async def count_user_webhooks(self, user_id: int) -> int:
        return await WebhookModel.objects.filter(user_id=user_id).acount()

    async def save_webhook(self, webhook: WebhookEntity) -> WebhookEntity:
        saved_webhook = await WebhookModel.objects.aget(id=webhook.unique_id)
        WebhookMapper.apply_to_model(saved_webhook, webhook)
        await saved_webhook.asave()

        return WebhookMapper.to_domain(saved_webhook)

    async def hard_delete_webhook(self, webhook_id: UUID) -> None:
        await WebhookModel.objects.filter(id=webhook_id).adelete()

    async def create_subscription(
        self,
        subscription: WebhookSubscriptionEntity,
    ) -> WebhookSubscriptionEntity:
        created_subscription = WebhookSubscriptionModel()
        WebhookSubscriptionMapper.apply_to_model(created_subscription, subscription)
        await created_subscription.asave()

        refreshed = await WebhookSubscriptionModel.objects.aget(id=created_subscription.id)
        return WebhookSubscriptionMapper.to_domain(refreshed)

    async def get_webhook_subscription_by_id(
        self,
        subscription_id: UUID,
        webhook_id: UUID,
    ) -> WebhookSubscriptionEntity:
        requested_subscription: WebhookSubscriptionModel = (
            await WebhookSubscriptionModel.objects.aget(
                id=subscription_id,
                webhook_id=webhook_id,
            )
        )

        return WebhookSubscriptionMapper.to_domain(requested_subscription)

    async def get_webhook_subscriptions(
        self,
        webhook_id: UUID,
    ) -> list[WebhookSubscriptionEntity]:
        queryset = WebhookSubscriptionModel.objects.filter(webhook_id=webhook_id).order_by(
            "created_at"
        )

        return [
            WebhookSubscriptionMapper.to_domain(subscription) async for subscription in queryset
        ]

    async def subscription_exists(self, webhook_id: UUID, event_type: str) -> bool:
        return await WebhookSubscriptionModel.objects.filter(
            webhook_id=webhook_id,
            event_type=event_type,
        ).aexists()

    async def hard_delete_subscription(self, subscription_id: UUID) -> None:
        await WebhookSubscriptionModel.objects.filter(id=subscription_id).adelete()
