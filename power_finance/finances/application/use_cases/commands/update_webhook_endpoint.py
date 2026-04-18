from dataclasses import dataclass
from uuid import UUID

from finances.domain.entities import Webhook

from ...db_utils import aatomic
from ...bootstrap import get_repository_registry
from ...dto_builders import webhook_to_dto
from ...dtos import WebhookDTO
from ...interfaces import WebhookRepository


@dataclass
class UpdateWebhookEndpointCommand:
    webhook_id: UUID
    user_id: int
    title: str | None = None
    url: str | None = None


class UpdateWebhookEndpointCommandHandler:
    webhook_repository: WebhookRepository

    def __init__(
            self,
            webhook_repository: WebhookRepository | None = None,
    ):
        registry = get_repository_registry()
        self.webhook_repository = webhook_repository or registry.webhook_repository

    async def _update_fields(self, webhook: Webhook, command: UpdateWebhookEndpointCommand) -> Webhook:
        if command.title is not None:
            webhook.title = command.title
        if command.url is not None:
            webhook.url = command.url

        return await self.webhook_repository.save_webhook(webhook)

    async def handle(self, command: UpdateWebhookEndpointCommand) -> WebhookDTO:
        async with aatomic():
            existing_webhook = await self.webhook_repository.get_user_webhook_by_id(
                webhook_id=command.webhook_id,
                user_id=command.user_id
            )

            updated_webhook = await self._update_fields(existing_webhook, command)

            return webhook_to_dto(updated_webhook)
