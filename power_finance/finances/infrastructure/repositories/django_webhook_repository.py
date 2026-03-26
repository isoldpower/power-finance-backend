from uuid import UUID
from django.core.exceptions import ObjectDoesNotExist

from finances.application.interfaces import WebhookRepository
from finances.application.dtos import WebhookSubscriptionDTO
from finances.domain.entities import WebhookType, Webhook

from ..mappers import WebhookMapper
from ..orm import WebhookEndpointModel, WebhookEventSubscriptionModel


class DjangoWebhookRepository(WebhookRepository):
    def subscribe_webhook_to_event(
            self,
            webhook: Webhook,
            event_type: WebhookType,
            user_id: int
    ) -> WebhookSubscriptionDTO:
        subscription_object = WebhookEventSubscriptionModel.objects.create(
            endpoint_id=webhook.id,
            event_type=event_type,
            is_active=True
        )

        return WebhookMapper.subscription_to_dto(subscription_object)

    def unsubscribe_webhook_from_event(
            self,
            webhook: Webhook,
            event_type: WebhookType,
            user_id: int,
    ) -> WebhookSubscriptionDTO:
        try:
            subscription_object = WebhookEventSubscriptionModel.objects.get(
                endpoint_id=webhook.id,
                endpoint__user_id=user_id,
                event_type=event_type,
                is_active=True
            )
        except WebhookEventSubscriptionModel.DoesNotExist:
            raise ObjectDoesNotExist(f"Subscription for event {event_type} not found.")

        subscription_dto = WebhookMapper.subscription_to_dto(subscription_object)
        subscription_object.delete()

        return subscription_dto

    def unsubscribe_webhook_by_id(
            self,
            subscription_id: UUID,
            webhook_id: UUID,
            user_id: int,
    ) -> WebhookSubscriptionDTO:
        try:
            subscription_object = WebhookEventSubscriptionModel.objects.get(
                id=subscription_id,
                endpoint_id=webhook_id,
                endpoint__user_id=user_id
            )
        except WebhookEventSubscriptionModel.DoesNotExist:
            raise ObjectDoesNotExist(f"Subscription with ID {subscription_id} not found for this webhook.")

        subscription_dto = WebhookMapper.subscription_to_dto(subscription_object)
        subscription_object.delete()

        return subscription_dto

    def get_subscription_by_id(
            self,
            subscription_id: UUID,
            webhook_id: UUID,
            user_id: int,
    ) -> WebhookSubscriptionDTO:
        try:
            subscription_object = WebhookEventSubscriptionModel.objects.get(
                id=subscription_id,
                endpoint_id=webhook_id,
                endpoint__user_id=user_id
            )
        except WebhookEventSubscriptionModel.DoesNotExist:
            raise ObjectDoesNotExist(f"Subscription with ID {subscription_id} not found for this webhook.")

        return WebhookMapper.subscription_to_dto(subscription_object)

    def create_webhook(self, webhook: Webhook) -> Webhook:
        new_webhook = WebhookEndpointModel()

        new_webhook.id = webhook.id
        WebhookMapper.update_model(new_webhook, webhook)
        new_webhook.save()

        return WebhookMapper.to_domain(new_webhook)

    def get_user_webhooks(self, user_id: int) -> list[Webhook]:
        requested_webhooks = WebhookEndpointModel.objects.filter(user_id=user_id)

        return [WebhookMapper.to_domain(webhook) for webhook in requested_webhooks]

    def get_webhooks_by_type(self, event_type: WebhookType, user_id: int) -> list[Webhook]:
        requested_webhooks = (WebhookEndpointModel.objects
            .filter(subscriptions__event_type=event_type, user_id=user_id)
            .distinct()
        )

        return [WebhookMapper.to_domain(webhook) for webhook in requested_webhooks]

    def get_webhook_by_id(self, webhook_id: str, user_id: int) -> Webhook:
        requested_webhook = WebhookEndpointModel.objects.get(
            user_id=user_id,
            id=webhook_id
        )

        return WebhookMapper.to_domain(requested_webhook)

    def delete_webhook_by_id(self, webhook_id: str, user_id: int) -> Webhook:
        try:
            requested_webhook: WebhookEndpointModel = WebhookEndpointModel.objects.get(
                user_id=user_id,
                id=webhook_id
            )
        except WebhookEndpointModel.DoesNotExist:
            raise ObjectDoesNotExist("Webhook with specified ID does not exist.")

        domain_webhook: Webhook = WebhookMapper.to_domain(requested_webhook)
        requested_webhook.delete()

        return domain_webhook

    def save_webhook(self, webhook: Webhook) -> Webhook:
        webhook_model = WebhookEndpointModel.objects.get(
            id=webhook.id,
            user_id=webhook.user_id,
        )

        updated_fields = WebhookMapper.get_changed_fields(webhook_model, webhook)
        WebhookMapper.update_model(webhook_model, webhook)

        webhook_model.save(update_fields=updated_fields)
        return WebhookMapper.to_domain(webhook_model)

