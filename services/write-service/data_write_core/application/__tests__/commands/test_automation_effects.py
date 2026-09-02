"""The closed set of things a rule can do.

The executors themselves are thin — each hands off to the ordinary command for
its slice — so what is worth pinning here is what a rule is NOT allowed to
decide, and the one detail the loop guard depends on.
"""

from uuid import UUID, uuid4

import pytest

from data_write_core.application.commands.automations.engine import EFFECT_EXECUTORS
from data_write_core.application.commands.automations.engine.effects import (
    AUTOMATION_KIND,
    AUTOMATION_RESOLUTIONS,
    raise_action,
    transfer,
)
from data_write_core.domain.automations import EffectType, RunContext
from data_write_core.domain.entities import ActionSource
from data_write_core.domain.value_objects import TransactionOrigin

from ._automation_fakes import EXTERNAL_ID, USER_ID, make_rule

FROM_WALLET = "11111111-1111-1111-1111-111111111111"
TO_WALLET = "22222222-2222-2222-2222-222222222222"


def context(subject_type: str = "transaction") -> RunContext:
    rule = make_rule(name="Savings sweep")

    return RunContext(
        user_id=USER_ID,
        user_external_id=EXTERNAL_ID,
        automation_id=rule.unique_id,
        automation_name=rule.name,
        subject_type=subject_type,
        subject_id=uuid4(),
    )


class Capture:
    """Stands in for a command handler, keeping the command it was given."""

    commands: list = []

    def __init__(self, *args, **kwargs) -> None:
        pass

    async def handle(self, command):
        Capture.commands.append(command)

        return None, 1


@pytest.fixture(autouse=True)
def _clear_captures():
    Capture.commands = []


def test_every_effect_in_the_vocabulary_has_an_executor():
    """A type with no executor is refused at run time rather than skipped, so a
    gap here is a rule that saves and then fails — catch it at build time."""

    assert set(EFFECT_EXECUTORS) == {member.value for member in EffectType}


# --- raise_action -----------------------------------------------------------


def test_the_choices_offered_are_the_backend_s_not_the_rule_s():
    """A user-authored rule cannot define `resolutions` — that would make them a
    free-form structure and reintroduce server-driven forms."""

    assert AUTOMATION_RESOLUTIONS
    assert not any(resolution.applies for resolution in AUTOMATION_RESOLUTIONS)
    assert any(resolution.dismissal for resolution in AUTOMATION_RESOLUTIONS)


async def test_an_automation_action_comes_from_the_scheduler_and_groups_by_its_rule(monkeypatch):
    """`group_key` is what makes a daily rule bump ONE row's `occurrences`
    instead of appending an action a day."""

    monkeypatch.setattr(raise_action, "RaiseActionCommandHandler", Capture)
    run = context()

    await EFFECT_EXECUTORS[EffectType.RAISE_ACTION].apply(
        {"severity": "warning", "title": "Low balance", "body": "Top up soon."},
        run,
    )

    command = Capture.commands[0]

    assert command.source == ActionSource.SCHEDULER
    assert command.kind == AUTOMATION_KIND
    assert command.group_key == f"automation:{run.automation_id}"
    assert command.resolutions == AUTOMATION_RESOLUTIONS


# --- transfer ---------------------------------------------------------------


async def test_a_transfer_is_two_entries_of_one_ordinary_chain(monkeypatch):
    """Identical to POST /transactions/chains, and subject to every rule that
    applies there — including a closed target wallet failing the run."""

    monkeypatch.setattr(transfer, "CreateTransactionChainCommandHandler", Capture)

    await EFFECT_EXECUTORS[EffectType.TRANSFER].apply(
        {
            "from_wallet_id": FROM_WALLET,
            "to_wallet_id": TO_WALLET,
            "money": {"amount": "25.00", "currency": "USD"},
        },
        context(),
    )

    entries = Capture.commands[0].entries

    assert [entry.wallet_id for entry in entries] == [UUID(FROM_WALLET), UUID(TO_WALLET)]
    assert [str(entry.transaction_type) for entry in entries] == ["expense", "income"]
    assert entries[1].after == entries[0].temporary_id


async def test_the_money_a_rule_moves_is_marked_as_the_engine_s_own(monkeypatch):
    """The loop guard. Without this mark a rule triggered by
    `transaction.created` would fire on the transactions it just created."""

    monkeypatch.setattr(transfer, "CreateTransactionChainCommandHandler", Capture)

    await EFFECT_EXECUTORS[EffectType.TRANSFER].apply(
        {
            "from_wallet_id": FROM_WALLET,
            "to_wallet_id": TO_WALLET,
            "money": {"amount": "25.00", "currency": "USD"},
        },
        context(),
    )

    assert all(
        entry.origin is TransactionOrigin.AUTOMATION for entry in Capture.commands[0].entries
    )


def test_a_client_cannot_claim_the_engine_s_origin():
    """Claiming `automation` on a hand-made transaction would be a way to make
    it invisible to every rule the user wrote."""

    from data_write_core.domain.value_objects import CLIENT_ORIGINS

    assert TransactionOrigin.AUTOMATION not in CLIENT_ORIGINS
