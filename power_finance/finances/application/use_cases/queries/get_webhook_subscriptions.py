from dataclasses import dataclass

from finances.application.dtos import WebhookSubscriptionDTO
from finances.application.interfaces import WebhookRepository

from finances.infrastructure.repositories import DjangoWebhookRepository

@dataclass(frozen=True)
class GetWebhookSubscriptionsQuery:
    webhook_id: str
    user_id: int

class GetWebhookSubscriptionsQueryHandler:
    webhook_repository: WebhookRepository

    def __init__(
            self,
            webhook_repository: WebhookRepository | None = None,
    ) -> None:
        self.webhook_repository = webhook_repository or DjangoWebhookRepository()

    def handle(self, query: GetWebhookSubscriptionsQuery) -> list[WebhookSubscriptionDTO]:
        return self.webhook_repository.get_subscriptions_by_webhook_id(
            webhook_id=query.webhook_id,
            user_id=query.user_id,
        )
