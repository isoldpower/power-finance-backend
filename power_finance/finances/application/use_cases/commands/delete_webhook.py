from dataclasses import dataclass
from uuid import UUID

from django.core.management import CommandError
from django.db import transaction

from finances.infrastructure.repositories import DjangoWebhookRepository

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
        self.webhook_repository = webhook_repository or DjangoWebhookRepository()

    @transaction.atomic
    def handle(self, command: DeleteWebhookCommand) -> WebhookDTO:
        deleted_webhook = self.webhook_repository.delete_webhook_by_id(
            UUID(command.webhook_id),
            command.user_id
        )

        if not deleted_webhook:
            raise CommandError(f"Error while deleting webhook with id {command.webhook_id}")
        return webhook_to_dto(deleted_webhook)