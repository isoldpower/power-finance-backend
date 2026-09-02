from dataclasses import dataclass
from typing import Any

from ..interfaces import (
    ActionRepository,
    AutomationRepository,
    CurrencyRepository,
    EventBus,
    GoalRepository,
    MoneyContainerRepository,
    MoneyFlowRepository,
    NotificationRepository,
    OutboxRepository,
    TransactionRepository,
    UserRepository,
    WalletRepository,
    WebhookRepository,
)


@dataclass(frozen=True)
class ImmudbConnection:
    client: Any
    transaction_token: Any


@dataclass(frozen=True)
class RepositoryRegistry:
    wallet_repository: "WalletRepository"
    goal_repository: "GoalRepository"
    money_container_repository: "MoneyContainerRepository"
    money_flow_repository: "MoneyFlowRepository"
    transaction_repository: "TransactionRepository"
    currency_repository: "CurrencyRepository"
    outbox_repository: "OutboxRepository"
    user_repository: "UserRepository"
    action_repository: "ActionRepository"
    automation_repository: "AutomationRepository"
    notification_repository: "NotificationRepository"
    webhook_repository: "WebhookRepository"


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
