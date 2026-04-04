from abc import ABC, abstractmethod
from uuid import UUID

from finances.domain.entities import WebhookPayload


class WebhookPayloadRepository(ABC):
    @abstractmethod
    def write_delivery_payload(self, payload: WebhookPayload) -> WebhookPayload:
        raise NotImplementedError()

    @abstractmethod
    def get_delivery_payload(self, delivery_id: UUID) -> WebhookPayload:
        raise NotImplementedError()
