from dataclasses import dataclass
from uuid import UUID

from ..dto_builders import webhook_to_dto
from ..dtos import WebhookDTO
from ..interfaces import WebhookRepository

from finances.infrastructure.repositories import DjangoWebhookRepository


@dataclass(frozen=True)
class GetWebhookQuery:
    user_id: int
    webhook_id: str


class GetWebhookQueryHandler:
    webhook_repository: WebhookRepository

    def __init__(
        self,
        webhook_repository: WebhookRepository | None = None,
    ):
        self.webhook_repository = webhook_repository or DjangoWebhookRepository()

    def handle(self, query: GetWebhookQuery) -> WebhookDTO:
        requested_webhook = self.webhook_repository.get_webhook_by_id(
            user_id=query.user_id,
            webhook_id=UUID(query.webhook_id)
        )

        return webhook_to_dto(requested_webhook)