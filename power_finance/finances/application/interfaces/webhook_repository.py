from abc import ABC, abstractmethod
from uuid import UUID

from finances.domain.entities import Webhook, WebhookType


class WebhookRepository(ABC):
    @abstractmethod
    def create_webhook(self, webhook: Webhook) -> Webhook:
        raise NotImplementedError

    @abstractmethod
    def get_webhooks_by_type(self, event_type: WebhookType, user_id: int) -> list[Webhook]:
        raise NotImplementedError

    @abstractmethod
    def get_webhook_by_id(self, webhook_id: UUID, user_id: int) -> Webhook:
        raise NotImplementedError

    @abstractmethod
    def delete_webhook_by_id(self, webhook_id: UUID, user_id: int) -> Webhook:
        raise NotImplementedError

    @abstractmethod
    def save_webhook(self, webhook: Webhook) -> Webhook:
        raise NotImplementedError