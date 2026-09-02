"""Which rules apply, and in what order.

Pure enough to test without a database, which is the point of it being a domain
service: evaluation order and the stale-condition rule are decisions, not
plumbing.
"""

from datetime import UTC, datetime
from decimal import Decimal

from data_write_core.domain.entities import (
    AutomationEffect,
    AutomationEntity,
    AutomationTrigger,
)
from data_write_core.domain.services import select_matching_rules

COFFEE = {"field_name": "name", "operator": "icontains", "value": "coffee"}
TEA = {"field_name": "name", "operator": "icontains", "value": "tea"}
WALLET_FIELD = {"field_name": "balance", "operator": "gte", "value": "1.00"}

TRANSACTION = {"name": "Blue Bottle Coffee", "amount": Decimal("-4.50")}


def make_rule(name: str, filter_body: dict | None, created_at: datetime) -> AutomationEntity:
    return AutomationEntity(
        id=f"1665b60e-bb7a-4360-8aa6-c1a578d8107{name[-1]}",
        user_id="7",
        user_external_id="user_abc",
        name=name,
        trigger=AutomationTrigger(
            type="event",
            event="transaction.created",
            filter_body=filter_body,
        ),
        effects=(AutomationEffect(type="notify", params={}),),
        created_at=created_at,
    )


def test_only_rules_whose_condition_holds_are_selected():
    matching = make_rule("rule1", COFFEE, datetime(2026, 1, 1, tzinfo=UTC))
    other = make_rule("rule2", TEA, datetime(2026, 2, 1, tzinfo=UTC))

    selection = select_matching_rules([matching, other], TRANSACTION)

    assert selection.matched == (matching,)


def test_an_unconditional_rule_is_always_selected():
    always = make_rule("rule1", None, datetime(2026, 1, 1, tzinfo=UTC))

    assert select_matching_rules([always], TRANSACTION).matched == (always,)


def test_the_order_handed_in_is_the_order_handed_back():
    """Evaluation is oldest-first so that when two rules set the same field the
    LAST one wins. Reordering here would make that outcome incidental."""

    older = make_rule("rule1", None, datetime(2026, 1, 1, tzinfo=UTC))
    newer = make_rule("rule2", None, datetime(2026, 6, 1, tzinfo=UTC))

    selection = select_matching_rules([older, newer], TRANSACTION)

    assert [rule.name for rule in selection.matched] == ["rule1", "rule2"]


def test_a_condition_its_policy_no_longer_accepts_is_set_aside_not_raised():
    """`balance` is a wallet field, so an event rule carrying it cannot be
    evaluated. Taking the rest of the user's rules down with it would make a
    tightened policy an outage."""

    stale = make_rule("rule1", WALLET_FIELD, datetime(2026, 1, 1, tzinfo=UTC))
    working = make_rule("rule2", None, datetime(2026, 6, 1, tzinfo=UTC))

    selection = select_matching_rules([stale, working], TRANSACTION)

    assert selection.matched == (working,)
    assert selection.unreadable == (stale,)


def test_nothing_matching_is_an_empty_selection_rather_than_a_failure():
    selection = select_matching_rules(
        [make_rule("rule1", TEA, datetime(2026, 1, 1, tzinfo=UTC))], TRANSACTION
    )

    assert selection.matched == ()
    assert selection.unreadable == ()
