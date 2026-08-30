from contextlib import AsyncExitStack
from types import TracebackType

from sqlalchemy.ext.asyncio import AsyncSession

from service_core.shared.db_connection import (
    session_scope,
)
from service_core.shared.kafka_outbox import (
    OutboxRepository,
    SqlAlchemyOutboxRepository,
)

from ..repositories import (
    AccountRepository,
    DispatchUnitOfWork,
    EntryRepository,
    ProjectedTransactionRepository,
    UserRepository,
)
from ._entered import entered
from .sqlalchemy_account_repository import SqlAlchemyAccountRepository
from .sqlalchemy_entry_repository import SqlAlchemyEntryRepository
from .sqlalchemy_transaction_repository import SqlAlchemyProjectedTransactionRepository
from .sqlalchemy_user_repository import SqlAlchemyUserRepository


class SqlAlchemyDispatchUnitOfWork(DispatchUnitOfWork):
    def __init__(self) -> None:
        self._stack: AsyncExitStack | None = None
        self._session: AsyncSession | None = None
        self._accounts: AccountRepository | None = None
        self._entries: EntryRepository | None = None
        self._transactions: ProjectedTransactionRepository | None = None
        self._users: UserRepository | None = None
        self._outbox: OutboxRepository | None = None

    async def __aenter__(self) -> "SqlAlchemyDispatchUnitOfWork":
        self._stack = AsyncExitStack()
        self._session = await self._stack.enter_async_context(session_scope())

        self._accounts = SqlAlchemyAccountRepository(self._session)
        self._entries = SqlAlchemyEntryRepository(self._session)
        self._transactions = SqlAlchemyProjectedTransactionRepository(self._session)
        self._users = SqlAlchemyUserRepository(self._session)
        self._outbox = SqlAlchemyOutboxRepository(self._session)

        return self

    async def __aexit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if self._stack is None:
            return

        try:
            await self._stack.__aexit__(exception_type, exception, traceback)
        finally:
            self._stack = None
            self._session = None
            self._accounts = None
            self._entries = None
            self._transactions = None
            self._users = None
            self._outbox = None

    @property
    def accounts(self) -> AccountRepository:
        return entered(self._accounts)

    @property
    def entries(self) -> EntryRepository:
        return entered(self._entries)

    @property
    def transactions(self) -> ProjectedTransactionRepository:
        return entered(self._transactions)

    @property
    def users(self) -> UserRepository:
        return entered(self._users)

    @property
    def outbox(self) -> OutboxRepository:
        return entered(self._outbox)
