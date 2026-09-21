from datetime import UTC, datetime
from decimal import Decimal

import pytest

from ..entities import FilterFieldPolicy, TypeVariant
from ..exceptions import InvalidOperationError, PolicyViolationError, UnknownNodeError
from ..matcher import matches
from ..policies import TRANSACTION_FILTER_POLICY

POLICY = {
    "name": FilterFieldPolicy(
        request_name="name",
        allowed_operators={"eq", "neq", "in", "contains", "icontains"},
        value_type=TypeVariant.STRING,
    ),
    "amount": FilterFieldPolicy(
        request_name="amount",
        allowed_operators={"eq", "neq", "gte", "lte", "gt", "lt"},
        value_type=TypeVariant.DECIMAL,
    ),
    "created_at": FilterFieldPolicy(
        request_name="created_at",
        allowed_operators={"gte", "lte", "gt", "lt"},
        value_type=TypeVariant.DATETIME,
    ),
    "wallet_id": FilterFieldPolicy(
        request_name="wallet_id",
        allowed_operators={"eq", "neq", "in"},
        value_type=TypeVariant.UUID,
    ),
    "favorite": FilterFieldPolicy(
        request_name="favorite",
        allowed_operators={"eq"},
        value_type=TypeVariant.BOOLEAN,
    ),
}

RECORD = {
    "name": "Blue Bottle Coffee",
    "amount": Decimal("-4.50"),
    "created_at": datetime(2026, 9, 1, 12, 0, tzinfo=UTC),
    "wallet_id": "1665b60e-bb7a-4360-8aa6-c1a578d81077",
    "favorite": True,
}


def match(node, record=None) -> bool:
    return matches(node, record if record is not None else RECORD, POLICY)


def test_absent_condition_always_matches():
    """`null` means "always" on the wire, and it has to mean the same thing to
    the engine — otherwise an unconditional rule would never fire."""

    assert matches(None, RECORD, POLICY) is True


def test_equality_on_a_string():
    assert match({"field_name": "name", "operator": "eq", "value": "Blue Bottle Coffee"})
    assert not match({"field_name": "name", "operator": "eq", "value": "Blue Bottle"})


def test_icontains_is_case_insensitive_and_contains_is_not():
    assert match({"field_name": "name", "operator": "icontains", "value": "COFFEE"})
    assert not match({"field_name": "name", "operator": "contains", "value": "COFFEE"})
    assert match({"field_name": "name", "operator": "contains", "value": "Coffee"})


def test_in_matches_any_element():
    assert match({"field_name": "name", "operator": "in", "value": ["Tea", "Blue Bottle Coffee"]})
    assert not match({"field_name": "name", "operator": "in", "value": ["Tea", "Cocoa"]})


def test_a_malformed_element_of_in_matches_nothing_without_sinking_the_rest():
    node = {
        "field_name": "wallet_id",
        "operator": "in",
        "value": ["not-a-uuid", RECORD["wallet_id"]],
    }

    assert match(node)


def test_in_against_a_non_list_does_not_match():
    assert not match({"field_name": "name", "operator": "in", "value": "Blue Bottle Coffee"})


@pytest.mark.parametrize(
    ("operator", "value", "expected"),
    [
        ("lt", "0.00", True),
        ("lt", "-10.00", False),
        ("gte", "-4.5", True),
        ("eq", "-4.5", True),
        ("gt", "-4.50", False),
        ("lte", "-4.500", True),
    ],
)
def test_decimals_compare_numerically_not_lexically(operator, value, expected):
    """ "9.00" is less than "10.00", and "-4.5" is the same amount as "-4.50" —
    neither of which is true of the strings."""

    assert match({"field_name": "amount", "operator": operator, "value": value}) is expected


def test_ten_is_greater_than_nine_despite_the_strings():
    record = {"amount": Decimal("10.00")}

    assert matches({"field_name": "amount", "operator": "gt", "value": "9.00"}, record, POLICY)


def test_datetimes_compare_as_instants():
    assert match({"field_name": "created_at", "operator": "gte", "value": "2026-09-01T00:00:00Z"})
    assert not match(
        {"field_name": "created_at", "operator": "lt", "value": "2026-08-01T00:00:00Z"}
    )


def test_naive_stored_timestamps_are_read_as_utc():
    record = {"created_at": datetime(2026, 9, 1, 12, 0)}

    assert matches(
        {"field_name": "created_at", "operator": "gte", "value": "2026-09-01T11:00:00Z"},
        record,
        POLICY,
    )


def test_uuids_compare_by_value_not_by_spelling():
    node = {
        "field_name": "wallet_id",
        "operator": "eq",
        "value": RECORD["wallet_id"].upper(),
    }

    assert match(node)


def test_booleans_accept_both_spellings():
    assert match({"field_name": "favorite", "operator": "eq", "value": True})
    assert match({"field_name": "favorite", "operator": "eq", "value": "true"})


def test_and_requires_every_child():
    node = {
        "and": [
            {"field_name": "name", "operator": "icontains", "value": "coffee"},
            {"field_name": "amount", "operator": "lt", "value": "0.00"},
        ]
    }

    assert match(node)

    node["and"][1]["value"] = "-100.00"

    assert not match(node)


def test_or_requires_only_one_child():
    node = {
        "or": [
            {"field_name": "name", "operator": "eq", "value": "Tea"},
            {"field_name": "amount", "operator": "lt", "value": "0.00"},
        ]
    }

    assert match(node)


def test_nested_groups_evaluate_inside_out():
    node = {
        "and": [
            {"field_name": "amount", "operator": "lt", "value": "0.00"},
            {
                "or": [
                    {"field_name": "name", "operator": "eq", "value": "Tea"},
                    {"field_name": "name", "operator": "icontains", "value": "bottle"},
                ]
            },
        ]
    }

    assert match(node)


def test_an_absent_field_satisfies_nothing_including_neq():
    """Absence is not inequality. A transaction with no category is not "a
    transaction whose category is not Dining" — it is one the rule has nothing
    to say about."""

    record = {"name": "Blue Bottle Coffee"}

    assert not matches(
        {"field_name": "amount", "operator": "neq", "value": "0.00"},
        record,
        POLICY,
    )


def test_an_uncomparable_stored_value_fails_to_match_rather_than_raising():
    """A corrupt row is not something a user's rule should learn about."""

    record = {"amount": "not-an-amount"}

    assert not matches({"field_name": "amount", "operator": "gt", "value": "0.00"}, record, POLICY)


def test_unknown_field_raises_the_same_error_the_validator_raises():
    with pytest.raises(PolicyViolationError):
        match({"field_name": "secret", "operator": "eq", "value": "x"})


def test_operator_outside_the_policy_raises():
    """The tree was validated when the rule was saved, but the policy can be
    tightened afterwards, and a rule stored under the old one must not quietly
    keep its privileges."""

    with pytest.raises(InvalidOperationError):
        match({"field_name": "amount", "operator": "icontains", "value": "4"})


def test_garbage_node_raises():
    with pytest.raises(UnknownNodeError):
        match({"unexpected": "shape"})


def test_a_transaction_record_matches_the_shipped_transactions_policy():
    """The policy a rule is VALIDATED against is the one it is MATCHED against;
    a divergence here is the silent failure the shared library exists to
    prevent."""

    record = {
        "name": "Blue Bottle Coffee",
        "category": "Dining",
        "amount": Decimal("-4.50"),
        "currency": "USD",
        "type": "expense",
        "origin": "manual",
    }
    node = {
        "and": [
            {"field_name": "name", "operator": "icontains", "value": "coffee"},
            {"field_name": "type", "operator": "eq", "value": "expense"},
            {"field_name": "amount", "operator": "lt", "value": "0.00"},
        ]
    }

    assert matches(node, record, TRANSACTION_FILTER_POLICY)
