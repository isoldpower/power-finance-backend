"""The grammar both services share.

These assertions are the reason this is a library: write-service checks an
automation's condition when the rule is SAVED, read-service checks the same
shape when a search runs, and a rule that validates on one side and cannot match
on the other is the failure mode a second policy table would produce.
"""

import pytest

from filter_grammar_py import (
    FILTER_MALFORMED_GROUP,
    FILTER_MALFORMED_NODE,
    FILTER_OPERATOR_NOT_ALLOWED,
    FILTER_UNKNOWN_FIELD,
    FILTER_VALUE_TYPE,
    FilterFieldPolicy,
    FilterParseError,
    TypeVariant,
    validate_filter_body,
)

POLICY = {
    "name": FilterFieldPolicy(
        request_name="name",
        allowed_operators={"eq", "neq", "icontains", "in"},
        value_type=TypeVariant.STRING,
    ),
    "amount": FilterFieldPolicy(
        request_name="amount",
        allowed_operators={"eq", "gte", "lte"},
        value_type=TypeVariant.DECIMAL,
    ),
}


def failure_of(node) -> FilterParseError:
    with pytest.raises(FilterParseError) as failure:
        validate_filter_body(node, POLICY)

    return failure.value


def test_a_well_formed_leaf_passes():
    validate_filter_body({"field_name": "name", "operator": "eq", "value": "Coffee"}, POLICY)


def test_nested_groups_pass():
    validate_filter_body(
        {
            "and": [
                {"field_name": "name", "operator": "icontains", "value": "coffee"},
                {
                    "or": [
                        {"field_name": "amount", "operator": "lte", "value": "25.00"},
                        {"field_name": "amount", "operator": "gte", "value": "1.00"},
                    ]
                },
            ]
        },
        POLICY,
    )


@pytest.mark.parametrize(
    ("node", "expected"),
    [
        ({"field_name": "secret", "operator": "eq", "value": "x"}, FILTER_UNKNOWN_FIELD),
        (
            {"field_name": "amount", "operator": "icontains", "value": "1"},
            FILTER_OPERATOR_NOT_ALLOWED,
        ),
        ({"field_name": "amount", "operator": "nope", "value": "1"}, FILTER_OPERATOR_NOT_ALLOWED),
        ({"field_name": "amount", "operator": "eq", "value": "not-money"}, FILTER_VALUE_TYPE),
        ({"and": []}, FILTER_MALFORMED_GROUP),
        (
            {
                "and": [{"field_name": "name", "operator": "eq", "value": "A"}],
                "or": [{"field_name": "name", "operator": "eq", "value": "B"}],
            },
            FILTER_MALFORMED_GROUP,
        ),
        ({"unexpected": "shape"}, FILTER_MALFORMED_NODE),
        ({"field_name": "name", "operator": "eq"}, FILTER_MALFORMED_NODE),
    ],
)
def test_each_kind_of_failure_carries_its_own_detail_code(node, expected):
    assert failure_of(node).detail_code == expected


def test_a_node_that_is_not_an_object_is_rejected():
    assert failure_of(["not", "an", "object"]).detail_code == FILTER_MALFORMED_NODE


def test_failure_names_the_offending_node_by_json_path():
    """A client has to highlight the condition that failed, so the path points
    INTO the tree rather than at the whole body."""

    failure = failure_of(
        {
            "and": [
                {"field_name": "name", "operator": "eq", "value": "A"},
                {
                    "or": [
                        {"field_name": "amount", "operator": "gte", "value": "1.00"},
                        {"field_name": "amount", "operator": "icontains", "value": "1"},
                    ]
                },
            ]
        }
    )

    assert failure.path == "filter_body.and[1].or[1].operator"


@pytest.mark.parametrize("value", [100, 100.0, "1e3", "+100.00"])
def test_decimal_fields_take_the_money_grammar(value):
    """A JSON number where an amount is expected means a client regressed to
    floats, and the filter grammar refuses it exactly as the request parsers do."""

    node = {"field_name": "amount", "operator": "gte", "value": value}

    assert failure_of(node).detail_code == FILTER_VALUE_TYPE


def test_an_empty_group_is_not_a_spelling_of_always():
    """`filter_body: null` already means "always". Two spellings of one thing is
    one too many, so an empty group is a malformed group."""

    assert failure_of({"or": []}).detail_code == FILTER_MALFORMED_GROUP
