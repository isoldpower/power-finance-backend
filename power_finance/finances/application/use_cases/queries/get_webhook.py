from dataclasses import dataclass
from uuid import UUID

from ...bootstrap import get_repository_registry
from ...dto_builders import webhook_to_dto
from ...dtos import WebhookDTO
from ...interfaces import WebhookRepository


@dataclass(frozen=True)
class GetWebhookQuery:
    user_id: int
    webhook_id: UUID


class GetWebhookQueryHandler:
    webhook_repository: WebhookRepository

    def __init__(
        self,
        webhook_repository: WebhookRepository | None = None,
    ):
        registry = get_repository_registry()
        self.webhook_repository = webhook_repository or registry.webhook_repository

    async def handle(self, query: GetWebhookQuery) -> WebhookDTO:
        requested_webhook = await self.webhook_repository.get_user_webhook_by_id(
            user_id=query.user_id,
            webhook_id=query.webhook_id
        )

        return webhook_to_dto(requested_webhook)
