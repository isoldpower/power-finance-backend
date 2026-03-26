from abc import ABC, abstractmethod

from finances.domain.events import (
    TransactionCreatedEvent,
    TransactionUpdatedEvent,
    TransactionDeletedEvent,
)


class EventPayloadFactory(ABC):
    @abstractmethod
    def from_transaction_created(self, event: TransactionCreatedEvent) -> dict:
        raise NotImplementedError()

    @abstractmethod
    def from_transaction_updated(self, event: TransactionUpdatedEvent) -> dict:
        raise NotImplementedError()

    @abstractmethod
    def from_transaction_deleted(self, event: TransactionDeletedEvent) -> dict:
        raise NotImplementedError()