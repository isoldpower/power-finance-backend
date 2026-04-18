from dataclasses import dataclass

from finances.domain.entities import Webhook, WebhookCreateData

from ...db_utils import aatomic
from ...bootstrap import get_repository_registry
from ...dto_builders import webhook_to_dto
from ...dtos import WebhookDTO
from ...interfaces import WebhookRepository


@dataclass
class CreateWebhookEndpointCommand:
    user_id: int
    title: str
    url: str


class CreateWebhookEndpointCommandHandler:
    webhook_repository: WebhookRepository

    def __init__(
            self,
            webhook_repository: WebhookRepository | None = None,
    ):
        registry = get_repository_registry()
        self.webhook_repository = webhook_repository or registry.webhook_repository

    async def handle(self, command: CreateWebhookEndpointCommand) -> WebhookDTO:
        async with aatomic():
            domain_webhook = Webhook.create(WebhookCreateData(
                title=command.title,
                url=command.url,
                user_id=command.user_id,
            ))
            database_webhook = await self.webhook_repository.create_webhook(domain_webhook)

            return webhook_to_dto(database_webhook)
