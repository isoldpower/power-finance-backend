from dataclasses import dataclass

from django.db import transaction

from finances.infrastructure.repositories import DjangoWebhookRepository
from finances.domain.entities import Webhook, WebhookCreateData

from ...dto_builders import webhook_to_dto
from ...dtos import WebhookDTO
from ...interfaces import WebhookRepository


@dataclass
class CreateWebhookEndpointCommand:
    user_id: int
    title: str
    url: str
    events: list[str]


class CreateWebhookEndpointCommandHandler:
    webhook_repository: WebhookRepository

    def __init__(
            self,
            webhook_repository: WebhookRepository | None = None,
    ):
        self.webhook_repository = webhook_repository or DjangoWebhookRepository()

    @transaction.atomic
    def handle(self, command: CreateWebhookEndpointCommand) -> WebhookDTO:
        domain_webhook = Webhook.create(WebhookCreateData(
            title=command.title,
            url=command.url,
            user_id=command.user_id,
            subscribed_events=[]
        ))
        database_webhook = self.webhook_repository.create_webhook(domain_webhook)

        return webhook_to_dto(database_webhook)