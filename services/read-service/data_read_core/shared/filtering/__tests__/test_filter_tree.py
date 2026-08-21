import pytest
from django.db.models import Q

from data_read_core.shared.http_contract import DetailCode, ErrorCode

from ..entities import FilterFieldPolicy, TypeVariant
from ..exceptions import (
    FilterParseError,
    InvalidGroupingError,
    InvalidOperationError,
    InvalidStructureError,
    PolicyViolationError,
)
from ..filter_tree import FilterTree

POLICY = {
    "name": FilterFieldPolicy(
        request_name="name",
        allowed_operators={"eq", "neq", "icontains", "contains", "in"},
        value_type=TypeVariant.STRING,
        model_lookup="title",
        es_field="title.keyword",
    ),
    "balance": FilterFieldPolicy(
        request_name="balance",
        allowed_operators={"eq", "gte", "lte", "gt", "lt"},
        value_type=TypeVariant.FLOAT,
        model_lookup="balance",
        es_field="balance",
    ),
}


def make_tree() -> FilterTree:
    return FilterTree(POLICY)


def test_leaf_resolves_to_q_with_lookup():
    resolved = make_tree().resolve(
        {"field_name": "name", "operator": "eq", "value": "Salary"},
    )

    assert resolved == Q(title="Salary")


def test_not_equal_resolves_to_negated_q():
    resolved = make_tree().resolve(
        {"field_name": "name", "operator": "neq", "value": "Salary"},
    )

    assert resolved == ~Q(title="Salary")


def test_and_group_resolves_to_combined_q():
    resolved = make_tree().resolve(
        {
            "and": [
                {"field_name": "name", "operator": "icontains", "value": "sal"},
                {"field_name": "balance", "operator": "gte", "value": "100"},
            ]
        }
    )

    assert resolved == (Q(title__icontains="sal") & Q(balance__gte="100"))


def test_leaf_resolves_to_es_term():
    resolved = make_tree().resolve_es(
        {"field_name": "name", "operator": "eq", "value": "Salary"},
    )

    assert resolved == {"term": {"title.keyword": "Salary"}}


def test_range_resolves_to_es_range():
    resolved = make_tree().resolve_es(
        {"field_name": "balance", "operator": "lt", "value": "50.5"},
    )

    assert resolved == {"range": {"balance": {"lt": "50.5"}}}


def test_nested_groups_resolve_to_es_bool():
    resolved = make_tree().resolve_es(
        {
            "or": [
                {"field_name": "name", "operator": "eq", "value": "A"},
                {
                    "and": [
                        {"field_name": "balance", "operator": "gte", "value": "1"},
                        {"field_name": "balance", "operator": "lte", "value": "2"},
                    ]
                },
            ]
        }
    )

    assert resolved == {
        "bool": {
            "should": [
                {"term": {"title.keyword": "A"}},
                {
                    "bool": {
                        "must": [
                            {"range": {"balance": {"gte": "1"}}},
                            {"range": {"balance": {"lte": "2"}}},
                        ]
                    }
                },
            ],
            "minimum_should_match": 1,
        }
    }


def test_in_operator_resolves_to_es_terms():
    resolved = make_tree().resolve_es(
        {"field_name": "name", "operator": "in", "value": ["A", "B"]},
    )

    assert resolved == {"terms": {"title.keyword": ["A", "B"]}}


def test_icontains_resolves_to_case_insensitive_wildcard():
    resolved = make_tree().resolve_es(
        {"field_name": "name", "operator": "icontains", "value": "sal*ry"},
    )

    assert resolved == {
        "wildcard": {
            "title.keyword": {
                "value": "*sal\\*ry*",
                "case_insensitive": True,
            }
        }
    }


def test_unknown_field_raises_policy_violation():
    with pytest.raises(PolicyViolationError):
        make_tree().resolve_es(
            {"field_name": "secret", "operator": "eq", "value": "x"},
        )


def test_forbidden_operator_raises():
    with pytest.raises(InvalidOperationError):
        make_tree().resolve_es(
            {"field_name": "balance", "operator": "icontains", "value": "1"},
        )


def test_invalid_value_type_raises():
    with pytest.raises(InvalidOperationError):
        make_tree().resolve_es(
            {"field_name": "balance", "operator": "eq", "value": "not-a-number"},
        )


def test_empty_group_raises():
    with pytest.raises(InvalidStructureError):
        make_tree().resolve_es({"and": []})


def test_mixed_group_keys_raise():
    with pytest.raises(InvalidGroupingError):
        make_tree().resolve_es(
            {
                "and": [{"field_name": "name", "operator": "eq", "value": "A"}],
                "or": [{"field_name": "name", "operator": "eq", "value": "B"}],
            }
        )


def test_garbage_node_raises():
    with pytest.raises(InvalidOperationError):
        make_tree().resolve_es({"unexpected": "shape"})


def test_filter_failures_are_validation_failures_with_detail_codes():
    """Every filter problem is a 422 `validation_failed`; what distinguishes
    them is `error.details[].code`."""

    with pytest.raises(PolicyViolationError) as failure:
        make_tree().resolve_es({"field_name": "secret", "operator": "eq", "value": "x"})

    assert failure.value.status_code == 422
    assert failure.value.code == ErrorCode.VALIDATION_FAILED
    assert failure.value.details[0].code is DetailCode.FILTER_UNKNOWN_FIELD


@pytest.mark.parametrize(
    ("node", "expected"),
    [
        (
            {"field_name": "balance", "operator": "icontains", "value": "1"},
            DetailCode.FILTER_OPERATOR_NOT_ALLOWED,
        ),
        (
            {"field_name": "balance", "operator": "eq", "value": "not-a-number"},
            DetailCode.FILTER_VALUE_TYPE,
        ),
        ({"and": []}, DetailCode.FILTER_MALFORMED_GROUP),
        (
            {
                "and": [{"field_name": "name", "operator": "eq", "value": "A"}],
                "or": [{"field_name": "name", "operator": "eq", "value": "B"}],
            },
            DetailCode.FILTER_MALFORMED_GROUP,
        ),
        ({"unexpected": "shape"}, DetailCode.FILTER_MALFORMED_NODE),
    ],
)
def test_each_kind_of_filter_failure_has_its_own_detail_code(node, expected):
    with pytest.raises(FilterParseError) as failure:
        make_tree().resolve_es(node)

    assert failure.value.details[0].code is expected


def test_failure_names_the_offending_node_by_json_path():
    """A client has to be able to highlight the condition that failed, which
    means the path points into the tree rather than at the whole body."""

    tree = {
        "and": [
            {"field_name": "name", "operator": "eq", "value": "A"},
            {
                "or": [
                    {"field_name": "balance", "operator": "gte", "value": "1"},
                    {"field_name": "balance", "operator": "icontains", "value": "1"},
                ]
            },
        ]
    }

    with pytest.raises(FilterParseError) as failure:
        make_tree().resolve_es(tree)

    assert failure.value.details[0].field == "filter_body.and[1].or[1].operator"


def test_decimal_fields_take_the_money_grammar():
    policy = {
        "amount": FilterFieldPolicy(
            request_name="amount",
            allowed_operators={"eq", "gte"},
            value_type=TypeVariant.DECIMAL,
            es_field="amount",
        )
    }

    assert FilterTree(policy).resolve_es(
        {"field_name": "amount", "operator": "gte", "value": "100.00"}
    ) == {"range": {"amount": {"gte": "100.00"}}}


@pytest.mark.parametrize("value", [100, 100.0, "1e3", "+100.00"])
def test_decimal_fields_reject_json_numbers_and_non_canonical_strings(value):
    policy = {
        "amount": FilterFieldPolicy(
            request_name="amount",
            allowed_operators={"eq", "gte"},
            value_type=TypeVariant.DECIMAL,
        )
    }

    with pytest.raises(FilterParseError) as failure:
        FilterTree(policy).resolve_es({"field_name": "amount", "operator": "gte", "value": value})

    assert failure.value.details[0].code is DetailCode.FILTER_VALUE_TYPE
