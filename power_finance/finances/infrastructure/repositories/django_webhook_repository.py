from uuid import UUID
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q

from finances.application.interfaces import WebhookRepository
from finances.application.dtos import WebhookSubscriptionDTO
from finances.domain.entities import WebhookType, Webhook, ResolvedFilterTree

from ..mappers import WebhookMapper
from ..orm import WebhookEndpointModel, WebhookEventSubscriptionModel


class DjangoWebhookRepository(WebhookRepository):
    async def get_subscriptions_by_webhook_id(self, webhook_id: UUID, user_id: int) -> list[WebhookSubscriptionDTO]:
        subscriptions = WebhookEventSubscriptionModel.objects.filter(
            endpoint_id=webhook_id,
            endpoint__user_id=user_id,
            is_active=True
        )

        return [WebhookMapper.subscription_to_dto(sub) async for sub in subscriptions]

    async def subscribe_webhook_to_event(
            self,
            webhook: Webhook,
            event_type: WebhookType,
            user_id: int
    ) -> WebhookSubscriptionDTO:
        subscription_object = await WebhookEventSubscriptionModel.objects.acreate(
            endpoint_id=webhook.id,
            event_type=event_type.value,
            is_active=True
        )

        return WebhookMapper.subscription_to_dto(subscription_object)

    async def unsubscribe_webhook_from_event(
            self,
            webhook: Webhook,
            event_type: WebhookType,
            user_id: int,
    ) -> WebhookSubscriptionDTO:
        try:
            subscription_object = await WebhookEventSubscriptionModel.objects.aget(
                endpoint_id=webhook.id,
                endpoint__user_id=user_id,
                event_type=event_type.value,
                is_active=True
            )
        except WebhookEventSubscriptionModel.DoesNotExist:
            raise ObjectDoesNotExist(f"Subscription for event {event_type} not found.")

        subscription_dto = WebhookMapper.subscription_to_dto(subscription_object)
        await subscription_object.adelete()

        return subscription_dto

    async def unsubscribe_webhook_by_id(
            self,
            subscription_id: UUID,
            webhook_id: UUID,
            user_id: int,
    ) -> WebhookSubscriptionDTO:
        try:
            subscription_object = await WebhookEventSubscriptionModel.objects.aget(
                id=subscription_id,
                endpoint_id=webhook_id,
                endpoint__user_id=user_id
            )
        except WebhookEventSubscriptionModel.DoesNotExist:
            raise ObjectDoesNotExist(f"Subscription with ID {subscription_id} not found for this webhook.")

        subscription_dto = WebhookMapper.subscription_to_dto(subscription_object)
        await subscription_object.adelete()

        return subscription_dto

    async def get_subscription_by_id(
            self,
            subscription_id: UUID,
            webhook_id: UUID,
            user_id: int,
    ) -> WebhookSubscriptionDTO:
        try:
            subscription_object = await WebhookEventSubscriptionModel.objects.aget(
                id=subscription_id,
                endpoint_id=webhook_id,
                endpoint__user_id=user_id
            )
        except WebhookEventSubscriptionModel.DoesNotExist:
            raise ObjectDoesNotExist(f"Subscription with ID {subscription_id} not found for this webhook.")

        return WebhookMapper.subscription_to_dto(subscription_object)

    async def create_webhook(self, webhook: Webhook) -> Webhook:
        new_webhook = WebhookEndpointModel()
        WebhookMapper.update_model(new_webhook, webhook)
        await new_webhook.asave()

        return WebhookMapper.to_domain(new_webhook)

    async def get_user_webhooks(self, user_id: int) -> list[Webhook]:
        requested_webhooks = WebhookEndpointModel.objects.filter(user_id=user_id)

        return [WebhookMapper.to_domain(webhook) async for webhook in requested_webhooks]

    async def get_webhooks_by_type(self, event_type: WebhookType, user_id: int) -> list[Webhook]:
        requested_webhooks = (WebhookEndpointModel.objects
            .filter(subscriptions__event_type=event_type.value, user_id=user_id)
            .distinct()
        )

        return [WebhookMapper.to_domain(webhook) async for webhook in requested_webhooks]

    async def get_user_webhook_by_id(self, webhook_id: str, user_id: int) -> Webhook:
        requested_webhook = await WebhookEndpointModel.objects.aget(
            user_id=user_id,
            id=webhook_id
        )

        return WebhookMapper.to_domain(requested_webhook)

    async def get_webhook_by_id(self, webhook_id: UUID) -> Webhook:
        requested_webhook = await WebhookEndpointModel.objects.aget(id=webhook_id)

        return WebhookMapper.to_domain(requested_webhook)

    async def delete_webhook_by_id(self, webhook_id: str, user_id: int) -> Webhook:
        try:
            requested_webhook: WebhookEndpointModel = await WebhookEndpointModel.objects.aget(
                user_id=user_id,
                id=webhook_id
            )
        except WebhookEndpointModel.DoesNotExist:
            raise ObjectDoesNotExist("Webhook with specified ID does not exist.")

        domain_webhook: Webhook = WebhookMapper.to_domain(requested_webhook)
        await requested_webhook.adelete()

        return domain_webhook

    async def save_webhook(self, webhook: Webhook) -> Webhook:
        webhook_model = await WebhookEndpointModel.objects.aget(
            id=webhook.id,
            user_id=webhook.user_id,
        )

        updated_fields = WebhookMapper.get_changed_fields(webhook_model, webhook)
        WebhookMapper.update_model(webhook_model, webhook)

        await webhook_model.asave(update_fields=updated_fields)
        return WebhookMapper.to_domain(webhook_model)

    async def list_webhooks_with_filters(self, tree: ResolvedFilterTree, user_id: int) -> list[Webhook]:
        filtered_webhooks = (WebhookEndpointModel.objects
            .filter(Q(user_id=user_id) & tree.django_query)
            .distinct())

        return [WebhookMapper.to_domain(webhook) async for webhook in filtered_webhooks]
