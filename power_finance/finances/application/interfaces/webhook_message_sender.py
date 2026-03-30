from abc import ABC, abstractmethod
from dataclasses import dataclass

from finances.domain.entities.webhook import Webhook


@dataclass(frozen=True)
class WebhookMessage:
    endpoint: Webhook
    payload: dict
    event_type: str


@dataclass(frozen=True)
class WebhookMessageResponse:
    status: int


class WebhookMessageSender(ABC):
    @abstractmethod
    def send_message(self, message: WebhookMessage) -> WebhookMessageResponse:
        raise NotImplementedError
