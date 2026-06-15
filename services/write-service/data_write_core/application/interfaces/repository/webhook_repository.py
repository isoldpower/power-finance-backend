from abc import ABC, abstractmethod
from uuid import UUID

from data_write_core.domain.entities import WebhookEntity, WebhookSubscriptionEntity


class WebhookRepository(ABC):
    @abstractmethod
    async def create_webhook(self, webhook: WebhookEntity) -> WebhookEntity:
        raise NotImplementedError()

    @abstractmethod
    async def get_user_webhook_by_id(self, webhook_id: UUID, user_id: int) -> WebhookEntity:
        raise NotImplementedError()

    @abstractmethod
    async def get_user_webhooks(
        self,
        user_id: int,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[WebhookEntity]:
        raise NotImplementedError()

    @abstractmethod
    async def count_user_webhooks(self, user_id: int) -> int:
        raise NotImplementedError()

    @abstractmethod
    async def save_webhook(self, webhook: WebhookEntity) -> WebhookEntity:
        raise NotImplementedError()

    @abstractmethod
    async def hard_delete_webhook(self, webhook_id: UUID) -> None:
        raise NotImplementedError()

    @abstractmethod
    async def create_subscription(
        self,
        subscription: WebhookSubscriptionEntity,
    ) -> WebhookSubscriptionEntity:
        raise NotImplementedError()

    @abstractmethod
    async def get_webhook_subscription_by_id(
        self,
        subscription_id: UUID,
        webhook_id: UUID,
    ) -> WebhookSubscriptionEntity:
        raise NotImplementedError()

    @abstractmethod
    async def get_webhook_subscriptions(
        self,
        webhook_id: UUID,
    ) -> list[WebhookSubscriptionEntity]:
        raise NotImplementedError()

    @abstractmethod
    async def subscription_exists(self, webhook_id: UUID, event_type: str) -> bool:
        raise NotImplementedError()

    @abstractmethod
    async def hard_delete_subscription(self, subscription_id: UUID) -> None:
        raise NotImplementedError()
