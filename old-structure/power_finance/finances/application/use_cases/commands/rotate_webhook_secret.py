from dataclasses import dataclass
from uuid import UUID

from ...db_utils import aatomic
from ...bootstrap import get_repository_registry
from ...dto_builders import webhook_to_dto
from ...dtos import WebhookDTO
from ...interfaces import WebhookRepository


@dataclass(frozen=True)
class RotateWebhookSecretCommand:
    webhook_id: UUID
    user_id: int


class RotateWebhookSecretCommandHandler:
    webhook_repository: WebhookRepository

    def __init__(
        self,
        webhook_repository: WebhookRepository | None = None,
    ):
        registry = get_repository_registry()
        self.webhook_repository = webhook_repository or registry.webhook_repository

    async def handle(self, command: RotateWebhookSecretCommand) -> WebhookDTO:
        async with aatomic():
            requested_webhook = await self.webhook_repository.get_user_webhook_by_id(
                webhook_id=command.webhook_id,
                user_id=command.user_id,
            )

            requested_webhook.rotate_secret()
            updated_webhook = await self.webhook_repository.save_webhook(requested_webhook)

            return webhook_to_dto(updated_webhook)
