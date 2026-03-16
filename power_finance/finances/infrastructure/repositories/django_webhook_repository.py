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