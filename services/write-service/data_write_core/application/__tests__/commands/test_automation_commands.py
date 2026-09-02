"""Authoring a rule, and everything a rule is refused for.

Refusing at CREATE time is the point: a rule that cannot work is one the user
should hear about while they are still looking at the form, not one that quietly
never fires.
"""

import pytest

from data_write_core.domain.automations import (
    AutomationRefusal,
    validate_effects,
    validate_trigger,
)

COFFEE = {
    "field_name": "name",
    "operator": "icontains",
    "value": "coffee",
}
CATEGORISE = {"type": "set_category", "params": {"category": "Dining"}}
NOTIFY = {"type": "notify", "params": {"severity": "info", "title": "Ran"}}


def refusal_of(call) -> AutomationRefusal:
    with pytest.raises(AutomationRefusal) as failure:
        call()

    return failure.value


# --- triggers ---------------------------------------------------------------


def test_an_event_trigger_with_a_condition_is_accepted():
    validate_trigger(
        {"type": "event", "event": "transaction.created", "filter_body": {"and": [COFFEE]}}
    )


def test_a_schedule_trigger_without_a_condition_is_accepted():
    """`filter_body: null` means "always"."""

    validate_trigger({"type": "schedule", "schedule": "monthly", "filter_body": None})


def test_sending_the_selector_that_does_not_belong_is_a_conflict():
    """Requests supply ONE of `event` / `schedule`; responses carry both."""

    refusal = refusal_of(
        lambda: validate_trigger(
            {"type": "event", "event": "transaction.created", "schedule": "daily"}
        )
    )

    assert refusal.detail_code == "trigger_field_conflict"
    assert refusal.path == "trigger.schedule"


def test_an_unknown_event_is_refused():
    assert (
        refusal_of(lambda: validate_trigger({"type": "event", "event": "wallet.exploded"})).path
        == "trigger.event"
    )


def test_an_unknown_trigger_type_is_refused():
    assert refusal_of(lambda: validate_trigger({"type": "webhook"})).path == "trigger.type"


def test_the_condition_is_checked_against_the_trigger_s_subject():
    """An event trigger validates against transactions. `zero_balance` is a
    wallet field, so it cannot appear on one."""

    refusal = refusal_of(
        lambda: validate_trigger(
            {
                "type": "event",
                "event": "transaction.created",
                "filter_body": {
                    "field_name": "zero_balance",
                    "operator": "eq",
                    "value": "0.00",
                },
            }
        )
    )

    assert refusal.detail_code == "filter_unknown_field"


def test_a_malformed_condition_names_the_offending_node():
    refusal = refusal_of(
        lambda: validate_trigger(
            {
                "type": "event",
                "event": "transaction.created",
                "filter_body": {"and": [COFFEE, {"or": []}]},
            }
        )
    )

    assert refusal.detail_code == "filter_malformed_group"
    assert refusal.path == "trigger.filter_body.and[1]"


# --- effects ----------------------------------------------------------------


def test_a_rule_needs_at_least_one_effect():
    """A rule with no effects matches and does nothing, which is never what the
    user meant."""

    assert refusal_of(lambda: validate_effects([], "event")).path == "effects"


def test_an_unknown_effect_type_is_refused():
    refusal = refusal_of(lambda: validate_effects([{"type": "run_script", "params": {}}], "event"))

    assert refusal.detail_code == "effect_unknown_type"


def test_set_category_cannot_apply_to_a_scheduled_rule():
    """A scheduled rule scans wallets and has no transaction to categorise."""

    refusal = refusal_of(lambda: validate_effects([CATEGORISE], "schedule"))

    assert refusal.detail_code == "effect_subject_mismatch"
    assert refusal.path == "effects[0].type"


def test_notify_applies_to_either_subject():
    validate_effects([NOTIFY], "event")
    validate_effects([NOTIFY], "schedule")


def test_params_must_be_exactly_what_the_effect_documents():
    """No other keys are accepted inside `params`: an unknown key is a typo the
    user should hear about, not a silently ignored setting."""

    refusal = refusal_of(
        lambda: validate_effects(
            [{"type": "set_category", "params": {"category": "D", "colour": "red"}}],
            "event",
        )
    )

    assert refusal.detail_code == "effect_params_invalid"


def test_a_missing_param_is_refused():
    assert (
        refusal_of(
            lambda: validate_effects([{"type": "notify", "params": {"title": "x"}}], "event")
        ).detail_code
        == "effect_params_invalid"
    )


def test_an_unknown_severity_is_refused():
    refusal = refusal_of(
        lambda: validate_effects(
            [{"type": "notify", "params": {"severity": "apocalyptic", "title": "x"}}],
            "event",
        )
    )

    assert refusal.path == "effects[0].params.severity"


def test_a_transfer_takes_money_as_a_decimal_string():
    """The same money grammar the rest of the API takes: a JSON number here
    means a client regressed to floats."""

    refusal = refusal_of(
        lambda: validate_effects(
            [
                {
                    "type": "transfer",
                    "params": {
                        "from_wallet_id": "9a1e4c2b-0d7f-4a11-9c33-2b7e5f8a1d40",
                        "to_wallet_id": "b21d7e40-9c3a-4f18-88de-1a5c6b0e7f92",
                        "money": {"amount": 200.0, "currency": "USD"},
                    },
                }
            ],
            "schedule",
        )
    )

    assert refusal.path == "effects[0].params.money.amount"


def test_a_transfer_to_the_same_wallet_is_refused():
    same = "9a1e4c2b-0d7f-4a11-9c33-2b7e5f8a1d40"
    refusal = refusal_of(
        lambda: validate_effects(
            [
                {
                    "type": "transfer",
                    "params": {
                        "from_wallet_id": same,
                        "to_wallet_id": same,
                        "money": {"amount": "200.00", "currency": "USD"},
                    },
                }
            ],
            "schedule",
        )
    )

    assert refusal.detail_code == "effect_params_invalid"


def test_a_well_formed_transfer_is_accepted():
    validate_effects(
        [
            {
                "type": "transfer",
                "params": {
                    "from_wallet_id": "9a1e4c2b-0d7f-4a11-9c33-2b7e5f8a1d40",
                    "to_wallet_id": "b21d7e40-9c3a-4f18-88de-1a5c6b0e7f92",
                    "money": {"amount": "200.00", "currency": "USD"},
                },
            }
        ],
        "schedule",
    )


# --- the rule registry ------------------------------------------------------


def test_every_effect_type_has_a_rule():
    """A type with no rule would save unvalidated and fail at run time, so the
    gap is caught here rather than in a user's automation."""

    from data_write_core.domain.automations import EFFECT_RULES, EffectType

    assert set(EFFECT_RULES) == {member.value for member in EffectType}


def test_each_rule_answers_for_its_own_type():
    from data_write_core.domain.automations import EFFECT_RULES

    assert all(effect_type == rule.effect_type for effect_type, rule in EFFECT_RULES.items())


def test_only_set_category_is_tied_to_a_subject():
    """Every other effect applies to a transaction and a wallet alike; tying one
    down is what `effect_subject_mismatch` reports."""

    from data_write_core.domain.automations import EFFECT_RULES

    tied = {effect_type for effect_type, rule in EFFECT_RULES.items() if rule.subject is not None}

    assert tied == {"set_category"}


def test_params_that_are_not_an_object_are_refused():
    refusal = refusal_of(
        lambda: validate_effects([{"type": "notify", "params": ["severity"]}], "event")
    )

    assert refusal.detail_code == "effect_params_invalid"
    assert refusal.path == "effects[0].params"


def test_an_effect_that_is_not_an_object_is_refused():
    assert refusal_of(lambda: validate_effects(["notify"], "event")).path == "effects[0]"


def test_an_effect_without_a_type_is_refused_as_an_unknown_type():
    assert (
        refusal_of(lambda: validate_effects([{"params": {}}], "event")).detail_code
        == "effect_unknown_type"
    )


def test_a_string_is_not_a_list_of_effects():
    """`effects` is an array; a bare string is not one effect, it is a client
    that got the shape wrong."""

    assert refusal_of(lambda: validate_effects("notify", "event")).path == "effects"


def test_a_transfer_currency_must_be_a_code_not_a_name():
    refusal = refusal_of(
        lambda: validate_effects(
            [
                {
                    "type": "transfer",
                    "params": {
                        "from_wallet_id": "9a1e4c2b-0d7f-4a11-9c33-2b7e5f8a1d40",
                        "to_wallet_id": "b21d7e40-9c3a-4f18-88de-1a5c6b0e7f92",
                        "money": {"amount": "200.00", "currency": "dollars"},
                    },
                }
            ],
            "schedule",
        )
    )

    assert refusal.path == "effects[0].params.money.currency"


def test_a_transfer_amount_must_be_positive():
    refusal = refusal_of(
        lambda: validate_effects(
            [
                {
                    "type": "transfer",
                    "params": {
                        "from_wallet_id": "9a1e4c2b-0d7f-4a11-9c33-2b7e5f8a1d40",
                        "to_wallet_id": "b21d7e40-9c3a-4f18-88de-1a5c6b0e7f92",
                        "money": {"amount": "-5.00", "currency": "USD"},
                    },
                }
            ],
            "schedule",
        )
    )

    assert refusal.path == "effects[0].params.money.amount"
