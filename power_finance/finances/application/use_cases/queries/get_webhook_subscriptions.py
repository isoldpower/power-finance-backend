from dataclasses import dataclass
from uuid import UUID

from ...bootstrap import get_repository_registry
from ...dtos import WebhookSubscriptionDTO
from ...interfaces import WebhookRepository


@dataclass(frozen=True)
class GetWebhookSubscriptionsQuery:
    webhook_id: UUID
    user_id: int


class GetWebhookSubscriptionsQueryHandler:
    webhook_repository: WebhookRepository

    def __init__(
            self,
            webhook_repository: WebhookRepository | None = None,
    ) -> None:
        registry = get_repository_registry()
        self.webhook_repository = webhook_repository or registry.webhook_repository

    async def handle(self, query: GetWebhookSubscriptionsQuery) -> list[WebhookSubscriptionDTO]:
        return await self.webhook_repository.get_subscriptions_by_webhook_id(
            webhook_id=query.webhook_id,
            user_id=query.user_id,
        )
