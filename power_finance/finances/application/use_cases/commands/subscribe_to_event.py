from dataclasses import dataclass
from uuid import UUID
from django.db import transaction

from finances.infrastructure.repositories import DjangoWebhookRepository
from finances.domain.entities import WebhookType

from ...dtos import WebhookSubscriptionDTO
from ...interfaces import WebhookRepository


@dataclass
class SubscribeToEventCommand:
    webhook_id: str
    user_id: int
    event_type: str


class SubscribeToEventCommandHandler:
    webhook_repository: WebhookRepository

    def __init__(
            self,
            webhook_repository: WebhookRepository | None = None,
    ):
        self.webhook_repository = webhook_repository or DjangoWebhookRepository()

    @transaction.atomic
    def handle(self, command: SubscribeToEventCommand) -> WebhookSubscriptionDTO:
        webhook = self.webhook_repository.get_webhook_by_id(
            webhook_id=UUID(command.webhook_id),
            user_id=command.user_id
        )

        try:
            event_type = WebhookType(command.event_type)
        except ValueError:
            raise ValueError(f"Invalid event type: {command.event_type}")

        return self.webhook_repository.subscribe_webhook_to_event(
            webhook=webhook,
            event_type=event_type,
            user_id=command.user_id
        )
