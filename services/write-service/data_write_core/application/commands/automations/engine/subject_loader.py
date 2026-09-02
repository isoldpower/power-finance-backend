from dataclasses import dataclass
from uuid import UUID

from filter_grammar_py import Record

from data_write_core.domain.automations import SubjectType
from data_write_core.domain.entities import WalletEntity
from data_write_core.domain.services import transaction_subject, wallet_subject
from data_write_core.domain.value_objects import TransactionOrigin

from ....interfaces import (
    GoalRepository,
    MoneyContainerRepository,
    MoneyFlowRepository,
    TransactionRepository,
    WalletRepository,
)
from ...loader_mixins import (
    LoadContainerMixin,
    LoadTransactionMixin,
)


@dataclass(frozen=True)
class LoadedSubject:
    record: Record
    subject_type: str
    subject_id: UUID


class SubjectLoader(LoadTransactionMixin, LoadContainerMixin):
    def __init__(
        self,
        transaction_repository: TransactionRepository,
        money_flow_repository: MoneyFlowRepository,
        wallet_repository: WalletRepository,
        goal_repository: GoalRepository,
        container_repository: MoneyContainerRepository,
    ) -> None:
        LoadTransactionMixin.__init__(
            self,
            transaction_repository,
            money_flow_repository,
        )
        LoadContainerMixin.__init__(
            self,
            container_repository=container_repository,
            wallet_repository=wallet_repository,
            goal_repository=goal_repository,
            money_flow_repository=money_flow_repository,
        )

    async def for_transaction(
        self,
        transaction_id: UUID,
        user_id: int,
    ) -> LoadedSubject | None:
        aggregate = await self.load_transaction_aggregate(
            transaction_id,
            user_id,
        )
        transaction = aggregate.root

        if transaction.origin == TransactionOrigin.AUTOMATION:
            return None
        if transaction.deleted_at is not None:
            return None

        container = await self.load_container_dto(
            transaction.container_id,
            user_id,
        )

        return LoadedSubject(
            record=transaction_subject(aggregate, container.currency),
            subject_type=SubjectType.TRANSACTION,
            subject_id=UUID(transaction.unique_id),
        )

    async def for_wallet(self, wallet: WalletEntity, user_id: int) -> LoadedSubject:
        aggregate = await self.load_container_aggregate(
            UUID(wallet.unique_id),
            user_id,
        )

        return LoadedSubject(
            record=wallet_subject(wallet, aggregate.balance),
            subject_type=SubjectType.WALLET,
            subject_id=UUID(wallet.unique_id),
        )
