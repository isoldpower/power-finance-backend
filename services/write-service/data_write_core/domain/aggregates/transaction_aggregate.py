from datetime import datetime
from decimal import Decimal
from uuid import UUID

from ..entities import MoneyFlowEntity, TransactionEntity
from ..entities.transaction import UNCHANGED
from ..events import TransactionDeletedEvent, TransactionUpdatedEvent
from ..exceptions import (
    InvalidTransactionAmountError,
    TransactionAlreadyCancelledError,
    TransactionDirectionChangeError,
)
from ..value_objects import (
    MoneyFlowData,
    TransactionMetadata,
    TransactionType,
)
from ._aggregate_root import AggregateRoot


class TransactionAggregate(AggregateRoot[TransactionEntity]):
    _flows: list[MoneyFlowEntity]

    def __init__(
        self,
        transaction_entity: TransactionEntity,
        flows: list[MoneyFlowEntity],
    ) -> None:
        super().__init__(root=transaction_entity)

        self._flows = list(flows)

    @property
    def flows(self) -> list[MoneyFlowEntity]:
        return list(self._flows)

    @property
    def amount(self) -> Decimal:
        return sum(
            (flow.amount for flow in self._flows if flow.cancels_other is None),
            Decimal("0"),
        )

    @property
    def ledger_effect(self) -> Decimal:
        return sum((flow.amount for flow in self._flows), Decimal("0"))

    @property
    def type(self) -> TransactionType:
        return TransactionEntity.type_for(self.amount)

    @property
    def origin_flow(self) -> MoneyFlowEntity:
        return next(flow for flow in self._flows if not flow.is_correction)

    @property
    def is_cancelled(self) -> bool:
        return self.root.deleted_at is not None

    def adjust(self, new_amount: Decimal, now: datetime | None = None) -> MoneyFlowEntity | None:
        if self.is_cancelled:
            raise TransactionAlreadyCancelledError(transaction_id=UUID(self.unique_id))
        if new_amount == Decimal("0"):
            raise InvalidTransactionAmountError(new_amount)
        if TransactionEntity.type_for(new_amount) is not self.type:
            raise TransactionDirectionChangeError(
                transaction_id=UUID(self.unique_id),
                current_type=str(self.type),
                requested_type=str(TransactionEntity.type_for(new_amount)),
            )

        current_amount = self.amount
        if new_amount == current_amount:
            return None

        moment = now or datetime.now()
        adjusting_flow = MoneyFlowEntity.create(
            user_id=int(self.root.user_id),
            created_at=moment,
            data=MoneyFlowData(
                transaction_id=UUID(self.unique_id),
                container_id=self.root.container_id,
                amount=new_amount - current_amount,
                adjusts_other=UUID(self.origin_flow.unique_id),
            ),
            _event_collector=self.event_collector,
        )
        self._flows.append(adjusting_flow)
        self.event_collector.collect(
            TransactionUpdatedEvent(
                transaction_id=UUID(self.unique_id),
                container_id=self.root.container_id,
                user_id=int(self.root.user_id),
                previous_amount=current_amount,
                new_amount=new_amount,
                updated_at=moment,
            )
        )

        return adjusting_flow

    def cancel(self, now: datetime) -> MoneyFlowEntity | None:
        if self.is_cancelled:
            return None

        outstanding = self.amount
        inverse_flow = MoneyFlowEntity.create(
            user_id=int(self.root.user_id),
            created_at=now,
            data=MoneyFlowData(
                transaction_id=UUID(self.unique_id),
                container_id=self.root.container_id,
                amount=-outstanding,
                cancels_other=UUID(self.origin_flow.unique_id),
            ),
            _event_collector=self.event_collector,
        )
        self._flows.append(inverse_flow)
        self.root.mark_cancelled(now)
        self.event_collector.collect(
            TransactionDeletedEvent(
                transaction_id=UUID(self.unique_id),
                container_id=self.root.container_id,
                user_id=int(self.root.user_id),
                amount=outstanding,
                cancelled_by=UUID(inverse_flow.unique_id),
                created_at=now,
            )
        )

        return inverse_flow

    def update_metadata(
        self,
        now: datetime,
        name: str | object = UNCHANGED,
        category: str | None | object = UNCHANGED,
        evidence_url: str | None | object = UNCHANGED,
    ) -> bool:
        return self.root.update_metadata(
            now=now,
            name=name,
            category=category,
            evidence_url=evidence_url,
        )

    def restore_metadata(self, snapshot: TransactionMetadata, now: datetime) -> None:
        self.root.apply(snapshot, now)
