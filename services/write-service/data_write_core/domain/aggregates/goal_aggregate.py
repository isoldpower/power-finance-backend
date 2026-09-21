from datetime import datetime
from decimal import Decimal
from uuid import UUID

from ..entities import BalanceCheckpointEntity, GoalEntity, MoneyFlowEntity
from ..entities.goal import UNCHANGED
from ..events import GoalDeletedEvent, GoalUpdatedEvent
from ..exceptions import GoalClosedError, GoalNotEmptyError
from ..value_objects import GoalData, MoneyContainerKind, MoneyContainerRef
from ._aggregate_root import AggregateRoot


class GoalAggregate(AggregateRoot[GoalEntity]):
    _checkpoint: BalanceCheckpointEntity | None
    _unsettled_flows: list[MoneyFlowEntity]

    def __init__(
        self,
        goal_entity: GoalEntity,
        unsettled_flows: list[MoneyFlowEntity],
        balance_checkpoint: BalanceCheckpointEntity | None,
    ) -> None:
        super().__init__(root=goal_entity)

        self._unsettled_flows = list(unsettled_flows)
        self._checkpoint = balance_checkpoint

    @property
    def progress(self) -> Decimal:
        base = self._checkpoint.balance if self._checkpoint else Decimal("0")
        unsettled = sum((flow.amount for flow in self._unsettled_flows), Decimal("0"))

        return base + unsettled

    @property
    def balance(self) -> Decimal:
        return self.progress

    @property
    def currency_code(self) -> str:
        return self.root.currency_code

    @property
    def is_closed(self) -> bool:
        return self.root.deleted_at is not None

    def as_reference(self) -> MoneyContainerRef:
        return MoneyContainerRef(
            id=UUID(self.unique_id),
            kind=MoneyContainerKind.GOAL,
            currency_code=self.root.currency_code,
            title=self.root.title,
            is_closed=self.is_closed,
        )

    @property
    def is_empty(self) -> bool:
        return self.progress == Decimal("0")

    @property
    def is_reached(self) -> bool:
        return self.progress >= self.root.target

    def record(self, flow: MoneyFlowEntity) -> None:
        if self.is_closed:
            raise GoalClosedError(UUID(self.unique_id))

        self._unsettled_flows.append(flow)

    def soft_delete(self, now: datetime) -> None:
        if self.root.deleted_at is not None:
            return

        if not self.is_empty:
            raise GoalNotEmptyError(progress=self.progress)

        self.root.mark_deleted(now)
        self.event_collector.collect(
            GoalDeletedEvent(
                goal_id=UUID(self.unique_id),
                user_id=int(self.root.user_id),
                deleted_at=now,
            )
        )

    def replace(self, data: GoalData, now: datetime) -> None:
        self.update_metadata(
            now=now,
            title=data.title,
            target=data.target,
            finish_at=data.finish_at,
            url=data.url,
        )

    def update_metadata(
        self,
        now: datetime,
        title: str | object = UNCHANGED,
        target: Decimal | object = UNCHANGED,
        finish_at: datetime | None | object = UNCHANGED,
        url: str | None | object = UNCHANGED,
    ) -> None:
        previous_title = self.root.title
        changed = self.root.update_metadata(
            now=now,
            title=title,
            target=target,
            finish_at=finish_at,
            url=url,
        )
        if not changed:
            return

        self.event_collector.collect(
            GoalUpdatedEvent(
                goal_id=UUID(self.unique_id),
                user_id=int(self.root.user_id),
                previous_title=previous_title,
                new_title=self.root.title,
                updated_at=now,
                target=self.root.target,
                finish_at=self.root.finish_at,
                url=self.root.url,
            )
        )
