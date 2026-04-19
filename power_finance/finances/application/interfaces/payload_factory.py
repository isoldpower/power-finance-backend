from abc import ABC, abstractmethod

from finances.domain.events import (
    TransactionCreatedEvent,
    TransactionDeletedEvent,
    WebhookDeliveryStatusChangedEvent,
)


class EventPayloadFactory(ABC):
    @abstractmethod
    def from_transaction_created(self, event: TransactionCreatedEvent) -> dict:
        raise NotImplementedError()

    @abstractmethod
    def from_transaction_deleted(self, event: TransactionDeletedEvent) -> dict:
        raise NotImplementedError()

    @abstractmethod
    def from_delivery_status_changed(self, event: WebhookDeliveryStatusChangedEvent) -> dict:
        raise NotImplementedError()