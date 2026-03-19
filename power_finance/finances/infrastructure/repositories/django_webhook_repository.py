from django.core.exceptions import ObjectDoesNotExist

from finances.application.interfaces import WebhookRepository
from finances.domain.entities import WebhookType, Webhook

from ..mappers import WebhookMapper
from ..orm import WebhookEndpointModel


class DjangoWebhookRepository(WebhookRepository):
    def create_webhook(self, webhook: Webhook) -> Webhook:
        new_webhook = WebhookEndpointModel()

        new_webhook.id = webhook.id
        WebhookMapper.update_model(new_webhook, webhook)
        new_webhook.save()

        return WebhookMapper.to_domain(new_webhook)

    def get_webhooks_by_type(self, event_type: WebhookType, user_id: int) -> list[Webhook]:
        requested_webhooks = WebhookEndpointModel.objects.filter(user_id=user_id)

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

