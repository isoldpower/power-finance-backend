from dataclasses import dataclass
from django.db import transaction

from finances.infrastructure.repositories import DjangoWebhookRepository
from finances.domain.entities import Webhook
from ..dto_builders import webhook_to_dto
from ..dtos import WebhookDTO
from ..interfaces import WebhookRepository


@dataclass
class UpdateWebhookEndpointCommand:
    webhook_id: str
    user_id: int
    title: str | None = None
    url: str | None = None
    events: list[str] | None = None


class UpdateWebhookEndpointCommandHandler:
    webhook_repository: WebhookRepository

    def __init__(
            self,
            webhook_repository: WebhookRepository | None = None,
    ):
        self.webhook_repository = webhook_repository or DjangoWebhookRepository()

    def _update_fields(self, webhook: Webhook, command: UpdateWebhookEndpointCommand) -> Webhook:
        if command.title is not None:
            webhook.title = command.title
        if command.url is not None:
            webhook.url = command.url
        # Note: subscribed_events handling is currently minimal in the domain/repo
        # but we follow the pattern for title and url.
        
        return self.webhook_repository.save_webhook(webhook)

    @transaction.atomic
    def handle(self, command: UpdateWebhookEndpointCommand) -> WebhookDTO:
        existing_webhook = self.webhook_repository.get_webhook_by_id(
            webhook_id=command.webhook_id,
            user_id=command.user_id
        )
        
        updated_webhook = self._update_fields(existing_webhook, command)

        return webhook_to_dto(updated_webhook)
