from dataclasses import dataclass

from django.core.exceptions import ObjectDoesNotExist

from finances.infrastructure.repositories import DjangoWebhookRepository
from finances.domain.entities import WebhookType

from ...dto_builders import webhook_to_dto
from ...dtos import WebhookDTO
from ...interfaces import WebhookRepository


@dataclass(frozen=True)
class ListWebhooksQuery:
    user_id: int


class ListWebhooksQueryHandler:
    webhooks_repository: WebhookRepository

    def __init__(
            self,
            webhooks_repository: WebhookRepository | None = None,
    ) -> None:
        self.webhooks_repository = webhooks_repository or DjangoWebhookRepository()

    def handle(self, request: ListWebhooksQuery) -> list[WebhookDTO]:
        try:
            typed_webhooks = self.webhooks_repository.get_webhooks_by_type(
                WebhookType.TransactionCreate,
                request.user_id,
            )

            return [webhook_to_dto(webhook) for webhook in typed_webhooks]
        except ObjectDoesNotExist as e:
            raise ObjectDoesNotExist(f"Requested webhook does not exist: {e}")
