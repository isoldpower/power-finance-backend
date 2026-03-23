from dataclasses import dataclass

from finances.infrastructure.repositories import DjangoWebhookRepository, DjangoWebhookDeliveryRepository
from finances.domain.entities import WebhookType

from ...interfaces import (
    WebhookMessageSender,
    WebhookMessage,
    WebhookDeliveryRepository,
)
from ...interfaces import (
    WebhookRepository,
)


@dataclass(frozen=True)
class WebhookDelivery:
    user_id: int
    payload: dict
    event_type: WebhookType


class WebhookDeliveryHandler:
    def __init__(
            self,
            message_sender: WebhookMessageSender,
            webhook_repository: WebhookRepository | None = None,
            delivery_repository: WebhookDeliveryRepository | None = None,
    ):
        self._message_sender = message_sender
        self._webhook_repository = webhook_repository or DjangoWebhookRepository()
        self._delivery_repository = delivery_repository or DjangoWebhookDeliveryRepository()

    def handle(self, delivery: WebhookDelivery) -> None:
        endpoints = self._webhook_repository.get_webhooks_by_type(
            event_type=delivery.event_type,
            user_id=delivery.user_id,
        )

        for endpoint in endpoints:
            response = self._message_sender.send_message(WebhookMessage(
                endpoint=endpoint,
                payload=delivery.payload,
                event_type=delivery.event_type,
            ))

