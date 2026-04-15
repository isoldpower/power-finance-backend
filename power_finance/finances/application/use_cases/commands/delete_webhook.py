from dataclasses import dataclass
from uuid import UUID
from django.core.management import CommandError
from django.db import transaction

from ...bootstrap import get_repository_registry
from ...dto_builders import webhook_to_dto
from ...dtos import WebhookDTO
from ...interfaces import WebhookRepository


@dataclass(frozen=True)
class DeleteWebhookCommand:
    webhook_id: str
    user_id: int


class DeleteWebhookCommandHandler:
    webhook_repository: WebhookRepository

    def __init__(
        self,
        webhook_repository: WebhookRepository | None = None,
    ):
        registry = get_repository_registry()
        self.webhook_repository = webhook_repository or registry.webhook_repository

    async def handle(self, command: DeleteWebhookCommand) -> WebhookDTO:
        async with transaction.atomic():
            deleted_webhook = await self.webhook_repository.delete_webhook_by_id(
                UUID(command.webhook_id),
                command.user_id
            )

            if not deleted_webhook:
                raise CommandError(f"Error while deleting webhook with id {command.webhook_id}")
            return webhook_to_dto(deleted_webhook)
