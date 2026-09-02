"""What a rule knows about itself.

Matching lives on the entity because the POLICY comes off the rule's own
trigger. That is the invariant worth a test: a rule is matched against the same
field set it was validated against when it was saved.
"""

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from filter_grammar_py import PolicyViolationError

from data_write_core.domain.entities import (
    AutomationEffect,
    AutomationEntity,
    AutomationTrigger,
)

COFFEE = {"field_name": "name", "operator": "icontains", "value": "coffee"}
RICH = {"field_name": "balance", "operator": "gte", "value": "100.00"}

TRANSACTION = {
    "name": "Blue Bottle Coffee",
    "amount": Decimal("-4.50"),
    "type": "expense",
}
WALLET = {"name": "Everyday", "balance": Decimal("500.00")}


def make_rule(trigger: AutomationTrigger) -> AutomationEntity:
    return AutomationEntity(
        id="1665b60e-bb7a-4360-8aa6-c1a578d81077",
        user_id="7",
        user_external_id="user_abc",
        name="Rule",
        trigger=trigger,
        effects=(AutomationEffect(type="notify", params={}),),
        created_at=datetime(2026, 9, 1, tzinfo=UTC),
    )


def test_an_event_rule_is_matched_against_the_transactions_policy():
    rule = make_rule(
        AutomationTrigger(type="event", event="transaction.created", filter_body=COFFEE)
    )

    assert rule.matches_subject(TRANSACTION)


def test_a_scheduled_rule_is_matched_against_the_wallets_policy():
    rule = make_rule(AutomationTrigger(type="schedule", schedule="daily", filter_body=RICH))

    assert rule.matches_subject(WALLET)


def test_a_rule_carries_its_policy_rather_than_being_handed_one():
    """`balance` is a wallet field. An event rule cannot be matched against it,
    even by a caller that would like to — which is what stops a rule from being
    validated against one field set and matched against another."""

    rule = make_rule(AutomationTrigger(type="event", event="transaction.created", filter_body=RICH))

    with pytest.raises(PolicyViolationError):
        rule.matches_subject(WALLET)


def test_a_rule_without_a_condition_always_matches():
    rule = make_rule(AutomationTrigger(type="event", event="transaction.created"))

    assert rule.matches_subject(TRANSACTION)


def test_a_condition_that_does_not_hold_does_not_match():
    tea = {"field_name": "name", "operator": "icontains", "value": "tea"}
    rule = make_rule(AutomationTrigger(type="event", event="transaction.created", filter_body=tea))

    assert not rule.matches_subject(TRANSACTION)


def test_a_snapshot_survives_the_edit_it_was_taken_before():
    """What the saga compensation restores. Taken off the entity rather than by
    reading the row again — two reads cost a query and can disagree."""

    rule = make_rule(
        AutomationTrigger(type="event", event="transaction.created", filter_body=COFFEE)
    )
    before = rule.snapshot()

    rule.replace_trigger(
        AutomationTrigger(type="event", event="transaction.updated", filter_body=None)
    )
    rule.set_enabled(False)

    assert before.trigger.filter_body == COFFEE
    assert before.enabled is True


def test_restoring_puts_the_rule_back_including_its_timestamps():
    """A compensation is not an edit, so `updated_at` goes back too."""

    rule = make_rule(
        AutomationTrigger(type="event", event="transaction.created", filter_body=COFFEE)
    )
    before = rule.snapshot()

    rule.replace_effects((AutomationEffect(type="set_category", params={"category": "X"}),))
    rule.soft_delete(datetime(2026, 9, 2, tzinfo=UTC))
    rule.restore(before)

    assert rule.trigger.filter_body == COFFEE
    assert rule.effects[0].type == "notify"
    assert rule.deleted_at is None
    assert rule.updated_at is None
