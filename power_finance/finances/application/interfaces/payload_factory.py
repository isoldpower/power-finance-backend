from abc import ABC, abstractmethod

from finances.domain.events import TransactionCreatedEvent


class EventPayloadFactory(ABC):
    @abstractmethod
    def from_transaction_created(self, event: TransactionCreatedEvent) -> dict:
        raise NotImplementedError()