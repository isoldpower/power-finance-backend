from datetime import datetime
from decimal import Decimal
from uuid import UUID

import pytest

from data_write_core.application.commands import (
    SoftDeleteGoalCommand,
    SoftDeleteGoalCommandHandler,
    UpdateExistingGoalCommand,
    UpdateExistingGoalCommandHandler,
)
from data_write_core.application.commands.goals import update_existing_goal

from ..queries.fakes import FakeGoalRepository, FakeMoneyFlowRepository, make_goal

pytestmark = pytest.mark.django_db(transaction=True)

GOAL_ID = "22222222-2222-2222-2222-222222222222"
USER_ID = 7
EXTERNAL_ID = "user_abc"


async def _accept_any_scale(amount, currency_code) -> None:
    return None


class FakeOutboxRepository:
    def __init__(self) -> None:
        self.entries: list = []

    async def get_latest_sequence(self) -> int:
        return 7

    async def append(self, entry) -> int:
        self.entries.append(entry)

        return 7


def soft_delete_handler(goal_repository, outbox_repository):
    return SoftDeleteGoalCommandHandler(
        goal_repository=goal_repository,
        money_flow_repository=FakeMoneyFlowRepository(),
        outbox_repository=outbox_repository,
    )


def update_handler(goal_repository, outbox_repository):
    return UpdateExistingGoalCommandHandler(
        goal_repository=goal_repository,
        money_flow_repository=FakeMoneyFlowRepository(),
        outbox_repository=outbox_repository,
    )


async def test_soft_delete_marks_the_goal_and_emits_one_entry():
    goal_repository = FakeGoalRepository([make_goal(GOAL_ID)])
    outbox_repository = FakeOutboxRepository()

    goal_dto, write_version = await soft_delete_handler(
        goal_repository,
        outbox_repository,
    ).handle(
        SoftDeleteGoalCommand(
            user_id=USER_ID,
            user_external_id=EXTERNAL_ID,
            goal_id=UUID(GOAL_ID),
        )
    )

    assert write_version == 7
    assert str(goal_dto.id) == GOAL_ID
    assert goal_repository.saved[-1].deleted_at is not None
    assert len(outbox_repository.entries) == 1
    assert outbox_repository.entries[0].aggregate_type == "goal"
    assert outbox_repository.entries[0].partition_key == EXTERNAL_ID


async def test_soft_delete_of_an_unknown_goal_emits_nothing():
    outbox_repository = FakeOutboxRepository()

    with pytest.raises(LookupError):
        await soft_delete_handler(FakeGoalRepository([]), outbox_repository).handle(
            SoftDeleteGoalCommand(
                user_id=USER_ID,
                user_external_id=EXTERNAL_ID,
                goal_id=UUID(GOAL_ID),
            )
        )

    assert outbox_repository.entries == []


async def test_update_renames_the_goal():
    goal_repository = FakeGoalRepository([make_goal(GOAL_ID, title="Before")])
    outbox_repository = FakeOutboxRepository()

    goal_dto, _ = await update_handler(goal_repository, outbox_repository).handle(
        UpdateExistingGoalCommand(
            user_id=USER_ID,
            user_external_id=EXTERNAL_ID,
            goal_id=UUID(GOAL_ID),
            new_name="After",
        )
    )

    assert goal_dto.name == "After"
    assert goal_repository.saved[-1].title == "After"
    assert len(outbox_repository.entries) == 1


async def test_update_can_move_the_target(monkeypatch):
    # Changing a target validates its scale against the currency, which is the
    # one thing this handler still reads off the bootstrapped registry.
    monkeypatch.setattr(update_existing_goal, "ensure_amount_scale", _accept_any_scale)
    goal_repository = FakeGoalRepository([make_goal(GOAL_ID, target="1000")])

    goal_dto, _ = await update_handler(goal_repository, FakeOutboxRepository()).handle(
        UpdateExistingGoalCommand(
            user_id=USER_ID,
            user_external_id=EXTERNAL_ID,
            goal_id=UUID(GOAL_ID),
            target=Decimal("2500"),
        )
    )

    assert goal_dto.target == Decimal("2500")


async def test_an_omitted_field_is_left_alone():
    created = datetime(2026, 1, 1)
    goal_repository = FakeGoalRepository(
        [make_goal(GOAL_ID, title="Keep", target="1000", created_at=created)]
    )

    goal_dto, _ = await update_handler(goal_repository, FakeOutboxRepository()).handle(
        UpdateExistingGoalCommand(
            user_id=USER_ID,
            user_external_id=EXTERNAL_ID,
            goal_id=UUID(GOAL_ID),
            new_name="Renamed",
        )
    )

    assert goal_dto.name == "Renamed"
    assert goal_dto.target == Decimal("1000"), "an omitted target must not be reset"
