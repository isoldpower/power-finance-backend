from dataclasses import dataclass
from django.core.exceptions import ObjectDoesNotExist

from ...bootstrap import get_repository_registry
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
        registry = get_repository_registry()
        self.webhooks_repository = webhooks_repository or registry.webhook_repository

    def handle(self, request: ListWebhooksQuery) -> list[WebhookDTO]:
        try:
            typed_webhooks = self.webhooks_repository.get_user_webhooks(
                user_id=request.user_id,
            )

            return [webhook_to_dto(webhook) for webhook in typed_webhooks]
        except ObjectDoesNotExist as e:
            raise ObjectDoesNotExist(f"Requested webhook does not exist: {e}")
