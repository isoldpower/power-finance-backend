from abc import ABC, abstractmethod
from uuid import UUID

from finances.domain.entities import Webhook, WebhookType, ResolvedFilterTree
from finances.application.dtos import WebhookSubscriptionDTO


class WebhookRepository(ABC):
    @abstractmethod
    def get_user_webhooks(self, user_id: int) -> list[Webhook]:
        raise NotImplementedError()

    @abstractmethod
    def get_subscriptions_by_webhook_id(self, webhook_id: UUID, user_id: int) -> list[WebhookSubscriptionDTO]:
        raise NotImplementedError()

    @abstractmethod
    def create_webhook(self, webhook: Webhook) -> Webhook:
        raise NotImplementedError()

    @abstractmethod
    def get_webhooks_by_type(self, event_type: WebhookType, user_id: int) -> list[Webhook]:
        raise NotImplementedError()

    @abstractmethod
    def get_webhook_by_id(self, webhook_id: UUID, user_id: int) -> Webhook:
        raise NotImplementedError()

    @abstractmethod
    def delete_webhook_by_id(self, webhook_id: UUID, user_id: int) -> Webhook:
        raise NotImplementedError()

    @abstractmethod
    def subscribe_webhook_to_event(
            self,
            webhook: Webhook,
            event_type: WebhookType,
            user_id: int,
    ) -> WebhookSubscriptionDTO:
        raise NotImplementedError()

    @abstractmethod
    def unsubscribe_webhook_from_event(
            self,
            webhook: Webhook,
            event_type: WebhookType,
            user_id: int,
    ) -> WebhookSubscriptionDTO:
        raise NotImplementedError()

    @abstractmethod
    def unsubscribe_webhook_by_id(
            self,
            subscription_id: UUID,
            webhook_id: UUID,
            user_id: int,
    ) -> WebhookSubscriptionDTO:
        raise NotImplementedError()

    @abstractmethod
    def get_subscription_by_id(
            self,
            subscription_id: UUID,
            webhook_id: UUID,
            user_id: int,
    ) -> WebhookSubscriptionDTO:
        raise NotImplementedError()

    @abstractmethod
    def save_webhook(self, webhook: Webhook) -> Webhook:
        raise NotImplementedError()

    @abstractmethod
    def list_webhooks_with_filters(self, tree: ResolvedFilterTree, user_id: int) -> list[Webhook]:
        raise NotImplementedError()