from dataclasses import dataclass
from typing import Any

from ..interfaces import (
    CurrencyRepository,
    EventBus,
    OutboxRepository,
    TransactionRepository,
    UserRepository,
    WalletRepository,
)


@dataclass(frozen=True)
class ImmudbConnection:
    client: Any
    transaction_token: Any


@dataclass(frozen=True)
class RepositoryRegistry:
    wallet_repository: "WalletRepository"
    transaction_repository: "TransactionRepository"
    currency_repository: "CurrencyRepository"
    outbox_repository: "OutboxRepository"
    user_repository: "UserRepository"


@dataclass
class ApplicationEnvironment:
    immudb_host: str
    immudb_port: int
    immudb_user: str
    immudb_password: str
    immudb_transactions_db: str = "transactions"


@dataclass
class ApplicationState:
    initialized: bool
    immudb: ImmudbConnection
    repository_registry: RepositoryRegistry
    event_bus: "EventBus"
