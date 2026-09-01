"""Answering the queue, and the two rules that keep it a queue.

An action is a DECISION: the choices come from the server as `resolutions`, and
answering is terminal.
"""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from data_write_core.application.commands import (
    ExpireLapsedActionsCommand,
    ExpireLapsedActionsCommandHandler,
    RaiseActionCommand,
    RaiseActionCommandHandler,
    ResolveActionCommand,
    ResolveActionCommandHandler,
)
from data_write_core.application.commands.actions import EmptyResolutionsError
from data_write_core.domain.entities import ActionEntity, ActionStatus
from data_write_core.domain.exceptions import (
    ActionAlreadyResolvedError,
    UnknownResolutionError,
)
from data_write_core.domain.value_objects import ActionResolution, ResolutionIntent

# The SAGA coordinator opens a real transaction around the write step, so
# these need a database even though the repositories are fakes.
pytestmark = pytest.mark.django_db(transaction=True)

USER_ID = 7
EXTERNAL_ID = "user_abc"
NOW = datetime(2026, 9, 1, tzinfo=UTC)

APPLY = ActionResolution(
    resolution_id="apply",
    label="Categorise as Groceries",
    intent=ResolutionIntent.PRIMARY,
    applies=True,
)
DISMISS = ActionResolution(
    resolution_id="dismiss",
    label="Ignore",
    intent=ResolutionIntent.SECONDARY,
    dismissal=True,
)


class FakeActionRepository:
    def __init__(self, actions: list[ActionEntity] | None = None) -> None:
        self.actions = {action.unique_id: action for action in actions or []}
        self.deleted: list[UUID] = []

    async def create_action(self, action: ActionEntity) -> ActionEntity:
        self.actions[action.unique_id] = action
        return action

    async def save_action(self, action: ActionEntity) -> ActionEntity:
        self.actions[action.unique_id] = action
        return action

    async def get_user_action_by_id(self, action_id: UUID, user_id: int) -> ActionEntity:
        return self.actions[str(action_id)]

    async def find_pending_by_group_key(self, user_id: int, group_key: str):
        for action in self.actions.values():
            if action.group_key == group_key and action.status == ActionStatus.PENDING:
                return action

        return None

    async def hard_delete_action(self, action_id: UUID) -> None:
        self.deleted.append(action_id)
        self.actions.pop(str(action_id), None)

    async def find_lapsed_pending(self, now: datetime, limit: int) -> list[ActionEntity]:
        return [
            action
            for action in self.actions.values()
            if action.status == ActionStatus.PENDING
            and action.expires_at is not None
            and action.expires_at <= now
        ][:limit]


class FakeOutboxRepository:
    def __init__(self) -> None:
        self.entries: list = []

    async def get_latest_sequence(self) -> int:
        return 42

    async def append(self, entry) -> int:
        self.entries.append(entry)
        return 42


def make_action(**overrides) -> ActionEntity:
    defaults = dict(
        id=str(uuid4()),
        user_id=str(USER_ID),
        user_external_id=EXTERNAL_ID,
        source="assistant",
        kind="uncategorized",
        severity="info",
        title="3 transactions need a category",
        body="",
        created_at=NOW,
        resolutions=(APPLY, DISMISS),
    )
    defaults.update(overrides)

    return ActionEntity(**defaults)


def raise_command(**overrides) -> RaiseActionCommand:
    defaults = dict(
        user_id=USER_ID,
        user_external_id=EXTERNAL_ID,
        source="scheduler",
        kind="insufficient_funds",
        title="Netflix charges tomorrow",
        resolutions=(APPLY, DISMISS),
    )
    defaults.update(overrides)

    return RaiseActionCommand(**defaults)


async def test_an_action_with_nothing_to_choose_is_refused():
    """`resolutions` is never empty. An action with nothing to choose is a
    notification, not an action."""

    handler = RaiseActionCommandHandler(FakeActionRepository(), FakeOutboxRepository())

    with pytest.raises(EmptyResolutionsError):
        await handler.handle(raise_command(resolutions=()))


async def test_a_recurring_condition_collapses_onto_one_row():
    """A scheduled check that fires daily until payday updates ONE action
    instead of appending a row per run and burying the queue it is trying to
    surface."""

    existing = make_action(group_key="recurring:netflix", source="scheduler")
    repository = FakeActionRepository([existing])
    handler = RaiseActionCommandHandler(repository, FakeOutboxRepository())

    action, _ = await handler.handle(raise_command(group_key="recurring:netflix"))

    assert len(repository.actions) == 1
    assert action.id == UUID(existing.unique_id)
    assert action.occurrences == 2
    assert action.last_seen_at > NOW


async def test_a_non_recurring_action_starts_at_one_occurrence():
    """Never 0 — one occurrence is one sighting."""

    repository = FakeActionRepository()
    handler = RaiseActionCommandHandler(repository, FakeOutboxRepository())

    action, _ = await handler.handle(raise_command())

    assert action.occurrences == 1
    assert action.group_key is None


async def test_two_actions_without_a_group_key_do_not_collapse():
    repository = FakeActionRepository()
    handler = RaiseActionCommandHandler(repository, FakeOutboxRepository())

    await handler.handle(raise_command())
    await handler.handle(raise_command())

    assert len(repository.actions) == 2


async def test_resolving_empties_the_choices_and_records_when():
    """A resolved action offers no further choices, and an empty array rather
    than a stale list is what stops a client re-rendering dead buttons."""

    action = make_action()
    repository = FakeActionRepository([action])
    handler = ResolveActionCommandHandler(repository, FakeOutboxRepository())

    resolved, write_version = await handler.handle(
        ResolveActionCommand(
            user_id=USER_ID,
            user_external_id=EXTERNAL_ID,
            action_id=UUID(action.unique_id),
            resolution_id="apply",
        )
    )

    assert resolved.action.status == "resolved"
    assert resolved.action.resolutions == ()
    assert resolved.action.resolved_at is not None
    assert resolved.applies is True
    assert write_version == 42


async def test_dismissal_produces_dismissed_rather_than_resolved():
    """The distinction is recorded for analytics: "how often is this
    recommendation ignored" is not answerable if both collapse to one state."""

    action = make_action()
    handler = ResolveActionCommandHandler(
        FakeActionRepository([action]),
        FakeOutboxRepository(),
    )

    resolved, _ = await handler.handle(
        ResolveActionCommand(
            user_id=USER_ID,
            user_external_id=EXTERNAL_ID,
            action_id=UUID(action.unique_id),
            resolution_id="dismiss",
        )
    )

    assert resolved.action.status == "dismissed"
    assert resolved.applies is False


async def test_an_id_valid_on_another_action_is_still_unknown_here():
    """`resolution_id` must be one of the ids offered on THIS action."""

    action = make_action(resolutions=(DISMISS,))
    handler = ResolveActionCommandHandler(
        FakeActionRepository([action]),
        FakeOutboxRepository(),
    )

    with pytest.raises(UnknownResolutionError):
        await handler.handle(
            ResolveActionCommand(
                user_id=USER_ID,
                user_external_id=EXTERNAL_ID,
                action_id=UUID(action.unique_id),
                resolution_id="apply",
            )
        )


@pytest.mark.parametrize("answered", ["resolved", "dismissed", "expired"])
async def test_answering_twice_is_a_conflict(answered: str):
    """A conflict rather than a validation error: the request was well-formed
    and would have succeeded earlier."""

    action = make_action(status=answered, resolutions=())
    handler = ResolveActionCommandHandler(
        FakeActionRepository([action]),
        FakeOutboxRepository(),
    )

    with pytest.raises(ActionAlreadyResolvedError):
        await handler.handle(
            ResolveActionCommand(
                user_id=USER_ID,
                user_external_id=EXTERNAL_ID,
                action_id=UUID(action.unique_id),
                resolution_id="apply",
            )
        )


async def test_the_sweep_expires_only_what_has_lapsed():
    lapsed = make_action(expires_at=NOW - timedelta(hours=1))
    future = make_action(expires_at=NOW + timedelta(hours=1))
    still_open = make_action()
    repository = FakeActionRepository([lapsed, future, still_open])
    handler = ExpireLapsedActionsCommandHandler(repository, FakeOutboxRepository())

    expired = await handler.handle(ExpireLapsedActionsCommand(now=NOW))

    assert expired == [lapsed.unique_id]
    assert lapsed.status == "expired"
    assert lapsed.resolutions == ()
    assert future.status == "pending"
    assert still_open.status == "pending"


async def test_an_expired_action_can_no_longer_be_answered():
    """Expiry is an answer like any other — it closes the queue entry."""

    lapsed = make_action(expires_at=NOW - timedelta(hours=1))
    repository = FakeActionRepository([lapsed])
    await ExpireLapsedActionsCommandHandler(repository, FakeOutboxRepository()).handle(
        ExpireLapsedActionsCommand(now=NOW)
    )

    with pytest.raises(ActionAlreadyResolvedError):
        await ResolveActionCommandHandler(repository, FakeOutboxRepository()).handle(
            ResolveActionCommand(
                user_id=USER_ID,
                user_external_id=EXTERNAL_ID,
                action_id=UUID(lapsed.unique_id),
                resolution_id="apply",
            )
        )
