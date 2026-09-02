"""Authoring a rule, through the handlers rather than the validators.

The validation rules have their own suite; what these cover is the part that
only the handlers can get wrong — what is written, what is published, and what
is put back when publishing fails.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from data_write_core.application.commands import (
    CreateAutomationCommand,
    CreateAutomationCommandHandler,
    DeleteAutomationCommand,
    DeleteAutomationCommandHandler,
    UpdateAutomationCommand,
    UpdateAutomationCommandHandler,
)
from data_write_core.domain.automations import AutomationRefusal
from data_write_core.domain.entities import (
    AutomationEffect,
    AutomationEntity,
    AutomationTrigger,
)

# The SAGA coordinator opens a real transaction around the write step, so these
# need a database even though the repositories are fakes.
pytestmark = pytest.mark.django_db(transaction=True)

USER_ID = 7
EXTERNAL_ID = "user_abc"
NOW = datetime(2026, 9, 1, tzinfo=UTC)

COFFEE = {"field_name": "name", "operator": "icontains", "value": "coffee"}
TEA = {"field_name": "name", "operator": "icontains", "value": "tea"}
EVENT_TRIGGER = {"type": "event", "event": "transaction.created", "filter_body": COFFEE}
CATEGORISE = [{"type": "set_category", "params": {"category": "Dining"}}]
NOTIFY = [{"type": "notify", "params": {"severity": "info", "title": "Ran"}}]


class FakeAutomationRepository:
    """Answers with a FRESH entity every read, exactly as the Django repository
    does — it maps a row to a new object each time. A fake that handed back one
    shared instance would make the update compensation look like it worked when
    it was only mutating the same object twice."""

    def __init__(self, automations: list[AutomationEntity] | None = None) -> None:
        self.rows: dict[str, dict] = {}
        for automation in automations or []:
            self.rows[automation.unique_id] = _as_row(automation)
        self.deleted: list[UUID] = []
        self.reads = 0

    async def create_automation(self, automation: AutomationEntity) -> AutomationEntity:
        self.rows[automation.unique_id] = _as_row(automation)

        return _from_row(self.rows[automation.unique_id])

    async def save_automation(self, automation: AutomationEntity) -> AutomationEntity:
        self.rows[automation.unique_id] = _as_row(automation)

        return _from_row(self.rows[automation.unique_id])

    async def get_user_automation_by_id(
        self,
        automation_id: UUID,
        user_id: int,
    ) -> AutomationEntity:
        self.reads += 1

        return _from_row(self.rows[str(automation_id)])

    async def hard_delete_automation(self, automation_id: UUID) -> None:
        self.deleted.append(automation_id)
        self.rows.pop(str(automation_id), None)

    def stored(self, automation_id: str) -> AutomationEntity:
        return _from_row(self.rows[automation_id])


def _as_row(automation: AutomationEntity) -> dict:
    return {
        "id": automation.unique_id,
        "user_id": automation.user_id,
        "user_external_id": automation.user_external_id,
        "name": automation.name,
        "icon": automation.icon,
        "enabled": automation.enabled,
        "trigger": automation.trigger,
        "effects": automation.effects,
        "created_at": automation.created_at,
        "updated_at": automation.updated_at,
        "deleted_at": automation.deleted_at,
    }


def _from_row(row: dict) -> AutomationEntity:
    return AutomationEntity(
        id=row["id"],
        user_id=row["user_id"],
        user_external_id=row["user_external_id"],
        name=row["name"],
        icon=row["icon"],
        enabled=row["enabled"],
        trigger=row["trigger"],
        effects=row["effects"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        deleted_at=row["deleted_at"],
    )


class FakeOutboxRepository:
    def __init__(self, fails: bool = False) -> None:
        self.entries: list = []
        self.fails = fails

    async def get_latest_sequence(self) -> int:
        return 42

    async def append(self, entry) -> int:
        if self.fails:
            raise RuntimeError("kafka outbox is down")

        self.entries.append(entry)

        return 42


def make_stored_rule(**overrides) -> AutomationEntity:
    defaults = dict(
        id=str(uuid4()),
        user_id=str(USER_ID),
        user_external_id=EXTERNAL_ID,
        name="Coffee",
        icon="tag",
        trigger=AutomationTrigger(
            type="event",
            event="transaction.created",
            filter_body=COFFEE,
        ),
        effects=(AutomationEffect(type="set_category", params={"category": "Dining"}),),
        created_at=NOW,
    )
    defaults.update(overrides)

    return AutomationEntity(**defaults)


def create_command(**overrides) -> CreateAutomationCommand:
    defaults = dict(
        user_id=USER_ID,
        user_external_id=EXTERNAL_ID,
        name="Auto-categorise coffee shops",
        trigger=EVENT_TRIGGER,
        effects=CATEGORISE,
    )
    defaults.update(overrides)

    return CreateAutomationCommand(**defaults)


# --- create -----------------------------------------------------------------


async def test_a_created_rule_is_written_and_published():
    repository, outbox = FakeAutomationRepository(), FakeOutboxRepository()

    rule, _ = await CreateAutomationCommandHandler(repository, outbox).handle(create_command())

    assert len(repository.rows) == 1
    assert [entry.event_type for entry in outbox.entries] == ["AutomationCreated"]
    assert rule.trigger.filter_body == COFFEE
    assert rule.effects[0].type == "set_category"


async def test_a_rule_defaults_to_enabled():
    """A rule created disabled is legitimate, but the common case is wanting it
    to work."""

    repository = FakeAutomationRepository()

    rule, _ = await CreateAutomationCommandHandler(repository, FakeOutboxRepository()).handle(
        create_command()
    )

    assert rule.enabled is True


async def test_an_invalid_rule_is_refused_before_anything_is_written():
    repository, outbox = FakeAutomationRepository(), FakeOutboxRepository()
    broken = create_command(trigger={"type": "event", "event": "wallet.exploded"})

    with pytest.raises(AutomationRefusal):
        await CreateAutomationCommandHandler(repository, outbox).handle(broken)

    assert repository.rows == {}
    assert outbox.entries == []


async def test_a_rule_nobody_heard_about_is_removed_again():
    """It would evaluate here and nowhere else, so a failed publish takes the
    row with it."""

    repository = FakeAutomationRepository()

    with pytest.raises(RuntimeError):
        await CreateAutomationCommandHandler(
            repository,
            FakeOutboxRepository(fails=True),
        ).handle(create_command())

    assert repository.rows == {}
    assert repository.deleted


# --- update -----------------------------------------------------------------


async def test_a_trigger_is_replaced_whole_rather_than_merged():
    """There is no way to say "change the third leaf", so a client editing a
    condition sends the complete new trigger."""

    stored = make_stored_rule()
    repository, outbox = FakeAutomationRepository([stored]), FakeOutboxRepository()

    rule, _ = await UpdateAutomationCommandHandler(repository, outbox).handle(
        UpdateAutomationCommand(
            user_id=USER_ID,
            user_external_id=EXTERNAL_ID,
            automation_id=UUID(stored.unique_id),
            trigger={"type": "event", "event": "transaction.updated", "filter_body": TEA},
        )
    )

    assert rule.trigger.event == "transaction.updated"
    assert rule.trigger.filter_body == TEA
    assert [entry.event_type for entry in outbox.entries] == ["AutomationUpdated"]


async def test_disabling_a_rule_leaves_everything_else_alone():
    stored = make_stored_rule()
    repository = FakeAutomationRepository([stored])

    rule, _ = await UpdateAutomationCommandHandler(repository, FakeOutboxRepository()).handle(
        UpdateAutomationCommand(
            user_id=USER_ID,
            user_external_id=EXTERNAL_ID,
            automation_id=UUID(stored.unique_id),
            enabled=False,
        )
    )

    assert rule.enabled is False
    assert rule.name == "Coffee"
    assert rule.trigger.filter_body == COFFEE
    assert rule.updated_at is not None


async def test_an_edit_reads_the_rule_once():
    """The compensation snapshot comes off the entity, not off a second read:
    two reads cost a query and are not taken under one transaction, so they can
    disagree about what "before" was."""

    stored = make_stored_rule()
    repository = FakeAutomationRepository([stored])

    await UpdateAutomationCommandHandler(repository, FakeOutboxRepository()).handle(
        UpdateAutomationCommand(
            user_id=USER_ID,
            user_external_id=EXTERNAL_ID,
            automation_id=UUID(stored.unique_id),
            enabled=False,
        )
    )

    assert repository.reads == 1


async def test_a_failed_publish_puts_the_previous_rule_back():
    """The compensation restores a snapshot taken before the edit."""

    stored = make_stored_rule()
    repository = FakeAutomationRepository([stored])

    with pytest.raises(RuntimeError):
        await UpdateAutomationCommandHandler(repository, FakeOutboxRepository(fails=True)).handle(
            UpdateAutomationCommand(
                user_id=USER_ID,
                user_external_id=EXTERNAL_ID,
                automation_id=UUID(stored.unique_id),
                trigger={"type": "event", "event": "transaction.updated", "filter_body": TEA},
                effects=NOTIFY,
            )
        )

    restored = repository.stored(stored.unique_id)

    assert restored.trigger.filter_body == COFFEE
    assert restored.trigger.event == "transaction.created"
    assert restored.effects[0].type == "set_category"


async def test_an_updated_condition_is_validated_before_it_is_stored():
    stored = make_stored_rule()
    repository, outbox = FakeAutomationRepository([stored]), FakeOutboxRepository()

    with pytest.raises(AutomationRefusal):
        await UpdateAutomationCommandHandler(repository, outbox).handle(
            UpdateAutomationCommand(
                user_id=USER_ID,
                user_external_id=EXTERNAL_ID,
                automation_id=UUID(stored.unique_id),
                trigger={"type": "event", "event": "transaction.created", "schedule": "daily"},
            )
        )

    assert repository.stored(stored.unique_id).trigger.event == "transaction.created"
    assert outbox.entries == []


# --- delete -----------------------------------------------------------------


async def test_a_deleted_rule_is_soft_deleted_and_returned():
    stored = make_stored_rule()
    repository, outbox = FakeAutomationRepository([stored]), FakeOutboxRepository()

    rule, _ = await DeleteAutomationCommandHandler(repository, outbox).handle(
        DeleteAutomationCommand(
            user_id=USER_ID,
            user_external_id=EXTERNAL_ID,
            automation_id=UUID(stored.unique_id),
        )
    )

    assert rule.deleted_at is not None
    assert repository.stored(stored.unique_id).deleted_at is not None
    assert [entry.event_type for entry in outbox.entries] == ["AutomationDeleted"]


async def test_a_failed_publish_undoes_the_delete():
    stored = make_stored_rule()
    repository = FakeAutomationRepository([stored])

    with pytest.raises(RuntimeError):
        await DeleteAutomationCommandHandler(repository, FakeOutboxRepository(fails=True)).handle(
            DeleteAutomationCommand(
                user_id=USER_ID,
                user_external_id=EXTERNAL_ID,
                automation_id=UUID(stored.unique_id),
            )
        )

    assert repository.stored(stored.unique_id).deleted_at is None
