from abc import ABC, abstractmethod
from collections.abc import Callable
from types import TracebackType

from service_core.shared.kafka_outbox import OutboxRepository

from .account_repository import AccountRepository
from .entry_repository import EntryRepository
from .transaction_repository import ProjectedTransactionRepository
from .user_repository import UserRepository


class RemovalUnitOfWork(ABC):
    @abstractmethod
    async def __aenter__(self) -> "RemovalUnitOfWork":
        raise NotImplementedError()

    @abstractmethod
    async def __aexit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        raise NotImplementedError()

    @property
    @abstractmethod
    def accounts(self) -> AccountRepository:
        raise NotImplementedError()

    @property
    @abstractmethod
    def entries(self) -> EntryRepository:
        raise NotImplementedError()

    @property
    @abstractmethod
    def transactions(self) -> ProjectedTransactionRepository:
        raise NotImplementedError()

    @property
    @abstractmethod
    def users(self) -> UserRepository:
        raise NotImplementedError()

    @property
    @abstractmethod
    def outbox(self) -> OutboxRepository:
        raise NotImplementedError()


UnitOfWorkFactory = Callable[[], RemovalUnitOfWork]
