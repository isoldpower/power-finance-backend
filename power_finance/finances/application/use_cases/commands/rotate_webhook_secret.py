from dataclasses import dataclass
from uuid import UUID

from django.db import transaction

from finances.infrastructure.repositories import DjangoWebhookRepository

from ...dto_builders import webhook_to_dto
from ...dtos import WebhookDTO
from ...interfaces import WebhookRepository


@dataclass(frozen=True)
class RotateWebhookSecretCommand:
    webhook_id: str
    user_id: int


class RotateWebhookSecretCommandHandler:
    webhook_repository: WebhookRepository

    def __init__(
        self,
        webhook_repository: WebhookRepository | None = None,
    ):
        self.webhook_repository = webhook_repository or DjangoWebhookRepository()

    @transaction.atomic
    def handle(self, command: RotateWebhookSecretCommand) -> WebhookDTO:
        requested_webhook = self.webhook_repository.get_webhook_by_id(
            webhook_id=UUID(command.webhook_id),
            user_id=command.user_id,
        )

        requested_webhook.rotate_secret()
        updated_webhook = self.webhook_repository.save_webhook(requested_webhook)

        return webhook_to_dto(updated_webhook)
