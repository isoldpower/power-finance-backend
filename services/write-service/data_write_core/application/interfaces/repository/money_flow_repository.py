from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID

from data_write_core.domain.entities import BalanceCheckpointEntity, MoneyFlowEntity


class MoneyFlowRepository(ABC):
    @abstractmethod
    async def get_user_flows(
        self,
        user_id: int,
    ) -> list[MoneyFlowEntity]:
        raise NotImplementedError()

    @abstractmethod
    async def get_user_flow_by_id(
        self,
        user_id: int,
        transaction_id: UUID,
    ) -> MoneyFlowEntity:
        raise NotImplementedError()

    @abstractmethod
    async def create_transaction(
        self,
        transaction: MoneyFlowEntity,
    ) -> MoneyFlowEntity:
        raise NotImplementedError()

    @abstractmethod
    async def delete_flow_by_id(
        self,
        user_id: int,
        transaction_id: UUID,
    ) -> MoneyFlowEntity:
        raise NotImplementedError()

    @abstractmethod
    async def get_cancelling_flow(
        self,
        transaction_id: UUID,
    ) -> MoneyFlowEntity | None:
        raise NotImplementedError()

    @abstractmethod
    async def get_adjusting_flow(
        self,
        transaction_id: UUID,
    ) -> MoneyFlowEntity | None:
        raise NotImplementedError()

    @abstractmethod
    async def get_unsettled_flows(
        self,
        wallet_id: UUID,
        settled_at: str | None = None,
    ) -> list[MoneyFlowEntity]:
        raise NotImplementedError()

    @abstractmethod
    async def get_flows_for_transaction(self, transaction_id: UUID) -> list[MoneyFlowEntity]:
        """Every ledger row belonging to one transaction, corrections included.
        Their sum is the transaction's amount."""

        raise NotImplementedError()

    @abstractmethod
    async def get_flows_for_transactions(
        self,
        transaction_ids: list[UUID],
    ) -> dict[UUID, list[MoneyFlowEntity]]:
        raise NotImplementedError()

    @abstractmethod
    async def get_wallet_flows_between(
        self,
        wallet_id: UUID,
        since: datetime | None,
        until: datetime | None,
    ) -> list[MoneyFlowEntity]:
        raise NotImplementedError()

    @abstractmethod
    async def get_checkpoint(
        self,
        wallet_id: UUID,
    ) -> BalanceCheckpointEntity | None:
        raise NotImplementedError()

    @abstractmethod
    async def save_checkpoint(
        self,
        checkpoint: BalanceCheckpointEntity,
    ) -> None:
        raise NotImplementedError()
