from typing import NamedTuple, TypedDict, Unpack

from ..bootstrap import get_repository_registry
from ..interfaces import (
    GoalRepository,
    MoneyContainerRepository,
    MoneyFlowRepository,
    OutboxRepository,
    TransactionRepository,
    WalletRepository,
)
from ._command_base import CommandHandlerBase, THandler
from ._loader_mixins import LoadContainerMixin, LoadTransactionMixin


class LedgerRepositories(NamedTuple):
    transaction_repository: TransactionRepository
    money_flow_repository: MoneyFlowRepository
    wallet_repository: WalletRepository
    outbox_repository: OutboxRepository
    goal_repository: GoalRepository
    container_repository: MoneyContainerRepository


class LedgerRepositoryOverrides(TypedDict, total=False):
    transaction_repository: TransactionRepository | None
    money_flow_repository: MoneyFlowRepository | None
    wallet_repository: WalletRepository | None
    outbox_repository: OutboxRepository | None
    goal_repository: GoalRepository | None
    container_repository: MoneyContainerRepository | None


def resolve_ledger_repositories(
    **overrides: Unpack[LedgerRepositoryOverrides],
) -> LedgerRepositories:
    return LedgerRepositories(
        transaction_repository=overrides.get("transaction_repository")
        or get_repository_registry().transaction_repository,
        money_flow_repository=overrides.get("money_flow_repository")
        or get_repository_registry().money_flow_repository,
        wallet_repository=overrides.get("wallet_repository")
        or get_repository_registry().wallet_repository,
        outbox_repository=overrides.get("outbox_repository")
        or get_repository_registry().outbox_repository,
        goal_repository=overrides.get("goal_repository")
        or get_repository_registry().goal_repository,
        container_repository=overrides.get("container_repository")
        or get_repository_registry().money_container_repository,
    )


class LedgerCommandHandlerBase(CommandHandlerBase[THandler], LoadContainerMixin):
    _repositories: LedgerRepositories
    _transaction_repository: TransactionRepository
    _money_flow_repository: MoneyFlowRepository
    _wallet_repository: WalletRepository
    _outbox_repository: OutboxRepository

    def __init__(self, **repositories: Unpack[LedgerRepositoryOverrides]) -> None:
        resolved = resolve_ledger_repositories(**repositories)

        LoadContainerMixin.__init__(
            self,
            container_repository=resolved.container_repository,
            wallet_repository=resolved.wallet_repository,
            goal_repository=resolved.goal_repository,
            money_flow_repository=resolved.money_flow_repository,
        )

        self._repositories = resolved
        self._transaction_repository = resolved.transaction_repository
        self._money_flow_repository = resolved.money_flow_repository
        self._wallet_repository = resolved.wallet_repository
        self._outbox_repository = resolved.outbox_repository


class LoadedTransactionCommandHandlerBase(LedgerCommandHandlerBase[THandler], LoadTransactionMixin):
    def __init__(self, **repositories: Unpack[LedgerRepositoryOverrides]) -> None:
        LedgerCommandHandlerBase.__init__(self, **repositories)
        LoadTransactionMixin.__init__(
            self,
            self._transaction_repository,
            self._money_flow_repository,
        )
