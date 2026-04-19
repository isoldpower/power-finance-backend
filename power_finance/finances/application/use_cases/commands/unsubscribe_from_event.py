from dataclasses import dataclass
from uuid import UUID

from ...db_utils import aatomic
from ...bootstrap import get_repository_registry
from ...dtos import WebhookSubscriptionDTO
from ...interfaces import WebhookRepository


@dataclass
class UnsubscribeFromEventCommand:
    subscription_id: str
    webhook_id: UUID
    user_id: int


class UnsubscribeFromEventCommandHandler:
    webhook_repository: WebhookRepository

    def __init__(
            self,
            webhook_repository: WebhookRepository | None = None,
    ):
        registry = get_repository_registry()
        self.webhook_repository = webhook_repository or registry.webhook_repository

    async def handle(self, command: UnsubscribeFromEventCommand) -> WebhookSubscriptionDTO:
        async with aatomic():
            return await self.webhook_repository.unsubscribe_webhook_by_id(
                subscription_id=UUID(command.subscription_id),
                webhook_id=command.webhook_id,
                user_id=command.user_id
            )
