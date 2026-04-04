from abc import abstractmethod, ABC
from uuid import UUID


class EventJobDispatcher(ABC):
    @abstractmethod
    def dispatch_transaction_created(self, transaction_id: UUID) -> None:
        raise NotImplementedError()