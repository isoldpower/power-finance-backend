from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from django.test import SimpleTestCase

from data_write_core.domain.aggregates import GoalAggregate
from data_write_core.domain.entities import (
    BalanceCheckpointEntity,
    GoalEntity,
    MoneyFlowEntity,
)
from data_write_core.domain.events import EventCollector, GoalDeletedEvent, GoalUpdatedEvent
from data_write_core.domain.exceptions import GoalClosedError, GoalNotEmptyError
from data_write_core.domain.value_objects import (
    GoalData,
    MoneyContainerKind,
    MoneyFlowData,
)

GOAL_ID = "33333333-3333-3333-3333-333333333333"


def _goal(
    *,
    goal_id: str = GOAL_ID,
    target: str = "500",
    deleted_at: datetime | None = None,
    collector: EventCollector | None = None,
) -> GoalEntity:
    return GoalEntity.create(
        id=goal_id,
        data=GoalData(title="New bike", currency_code="USD", target=Decimal(target)),
        user_id="9",
        created_at=datetime(2026, 1, 1),
        deleted_at=deleted_at,
        _event_collector=collector or EventCollector(),
    )


def _flow(amount: str, container_id: str = GOAL_ID) -> MoneyFlowEntity:
    return MoneyFlowEntity.from_persistence(
        id=uuid4(),
        user_id=9,
        created_at=datetime(2026, 1, 2),
        data=MoneyFlowData(
            transaction_id=uuid4(),
            container_id=UUID(container_id),
            amount=Decimal(amount),
        ),
    )


def _aggregate(*amounts: str, goal: GoalEntity | None = None, checkpoint=None) -> GoalAggregate:
    return GoalAggregate(
        goal_entity=goal or _goal(),
        unsettled_flows=[_flow(amount) for amount in amounts],
        balance_checkpoint=checkpoint,
    )


class GoalProgressTests(SimpleTestCase):
    def test_a_fresh_goal_holds_nothing(self) -> None:
        assert _aggregate().progress == Decimal("0")

    def test_progress_folds_the_unsettled_flows(self) -> None:
        assert _aggregate("30", "20").progress == Decimal("50")

    def test_progress_starts_from_the_checkpoint(self) -> None:
        aggregate = _aggregate(
            "20",
            checkpoint=BalanceCheckpointEntity(
                id=GOAL_ID,
                created_at=datetime(2026, 1, 1),
                balance=Decimal("100"),
            ),
        )

        assert aggregate.progress == Decimal("120")

    def test_draining_a_goal_reduces_progress(self) -> None:
        assert _aggregate("50", "-20").progress == Decimal("30")

    def test_balance_is_the_container_name_for_progress(self) -> None:
        """`MoneyContainerAggregate` reads `balance`; the goal endpoints read
        `progress`. They must never disagree."""

        aggregate = _aggregate("30")

        assert aggregate.balance == aggregate.progress

    def test_the_flow_list_is_copied_not_aliased(self) -> None:
        flows = [_flow("30")]
        aggregate = GoalAggregate(
            goal_entity=_goal(),
            unsettled_flows=flows,
            balance_checkpoint=None,
        )
        flows.append(_flow("70"))

        assert aggregate.progress == Decimal("30")


class GoalReachedTests(SimpleTestCase):
    def test_a_goal_below_target_is_not_reached(self) -> None:
        assert _aggregate("100").is_reached is False

    def test_hitting_the_target_exactly_counts(self) -> None:
        assert _aggregate("500").is_reached is True

    def test_overshooting_counts_too(self) -> None:
        assert _aggregate("600").is_reached is True

    def test_reaching_a_target_does_not_close_the_goal(self) -> None:
        """A reached goal keeps taking flows. Completion is a display fact, not a
        state change."""

        aggregate = _aggregate("600")

        aggregate.record(_flow("10"))

        assert aggregate.progress == Decimal("610")
        assert aggregate.root.deleted_at is None


class GoalRecordTests(SimpleTestCase):
    def test_recording_moves_progress(self) -> None:
        aggregate = _aggregate()

        aggregate.record(_flow("30"))

        assert aggregate.progress == Decimal("30")

    def test_recording_emits_nothing(self) -> None:
        aggregate = _aggregate()

        aggregate.record(_flow("30"))

        assert aggregate.pull_events() == []

    def test_a_closed_goal_refuses_new_money(self) -> None:
        aggregate = GoalAggregate(
            goal_entity=_goal(deleted_at=datetime(2026, 2, 1)),
            unsettled_flows=[],
            balance_checkpoint=None,
        )

        with pytest.raises(GoalClosedError):
            aggregate.record(_flow("30"))


class GoalCloseTests(SimpleTestCase):
    def test_an_empty_goal_closes(self) -> None:
        aggregate = _aggregate()

        aggregate.soft_delete(now=datetime(2026, 2, 1))

        assert aggregate.root.deleted_at == datetime(2026, 2, 1)

    def test_closing_emits_the_deletion(self) -> None:
        aggregate = _aggregate()

        aggregate.soft_delete(now=datetime(2026, 2, 1))
        events = aggregate.pull_events()

        assert [type(event) for event in events] == [GoalDeletedEvent]
        assert events[0].goal_id == UUID(GOAL_ID)

    def test_a_goal_holding_money_refuses_to_close(self) -> None:
        aggregate = _aggregate("30")

        with pytest.raises(GoalNotEmptyError) as raised:
            aggregate.soft_delete(now=datetime(2026, 2, 1))

        assert raised.value.progress == Decimal("30")

    def test_a_drained_goal_closes(self) -> None:
        """The refusal is about the balance, not about having had one."""

        aggregate = _aggregate("30", "-30")

        aggregate.soft_delete(now=datetime(2026, 2, 1))

        assert aggregate.root.deleted_at is not None

    def test_an_overdrawn_goal_also_refuses(self) -> None:
        aggregate = _aggregate("30", "-50")

        with pytest.raises(GoalNotEmptyError):
            aggregate.soft_delete(now=datetime(2026, 2, 1))

    def test_closing_twice_is_a_no_op(self) -> None:
        aggregate = _aggregate()
        aggregate.soft_delete(now=datetime(2026, 2, 1))
        aggregate.pull_events()

        aggregate.soft_delete(now=datetime(2026, 3, 1))

        assert aggregate.root.deleted_at == datetime(2026, 2, 1)
        assert aggregate.pull_events() == []


class GoalMetadataTests(SimpleTestCase):
    def test_updating_emits_the_full_new_state(self) -> None:
        aggregate = _aggregate()

        aggregate.update_metadata(
            now=datetime(2026, 2, 1), title="Better bike", target=Decimal("900")
        )
        events = aggregate.pull_events()

        assert [type(event) for event in events] == [GoalUpdatedEvent]
        assert events[0].previous_title == "New bike"
        assert events[0].new_title == "Better bike"
        assert events[0].target == Decimal("900")

    def test_an_update_that_changes_nothing_emits_nothing(self) -> None:
        aggregate = _aggregate()

        aggregate.update_metadata(now=datetime(2026, 2, 1), title="New bike")

        assert aggregate.pull_events() == []

    def test_updating_never_touches_progress(self) -> None:
        aggregate = _aggregate("30")

        aggregate.update_metadata(now=datetime(2026, 2, 1), target=Decimal("900"))

        assert aggregate.progress == Decimal("30")

    def test_the_currency_is_not_restorable_through_a_snapshot(self) -> None:
        """`apply` deliberately leaves `currency_code` alone: it never changes, so
        writing it back would be the only path by which a bug could move it."""

        aggregate = _aggregate()
        snapshot = aggregate.root.snapshot()
        snapshot.currency_code = "JPY"

        aggregate.root.apply(snapshot, datetime(2026, 2, 1))

        assert aggregate.root.currency_code == "USD"


class GoalContainerTests(SimpleTestCase):
    def test_a_goal_presents_itself_as_a_goal_container(self) -> None:
        reference = _aggregate().as_reference()

        assert reference.kind is MoneyContainerKind.GOAL
        assert reference.is_goal is True
        assert reference.id == UUID(GOAL_ID)
        assert reference.currency_code == "USD"
        assert reference.title == "New bike"

    def test_a_closed_goal_says_so_in_its_reference(self) -> None:
        aggregate = GoalAggregate(
            goal_entity=_goal(deleted_at=datetime(2026, 2, 1)),
            unsettled_flows=[],
            balance_checkpoint=None,
        )

        assert aggregate.as_reference().is_closed is True
