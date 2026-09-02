from typing import Any

from .entities import ComparisonOperator, FilterPolicy
from .exceptions import ROOT_PATH, InvalidOperationError, PolicyViolationError
from .shapes import FIELD_NAME_KEY, OPERATOR_KEY, GroupShape, LeafShape, shape_of

KNOWN_OPERATORS = frozenset(member.value for member in ComparisonOperator)


def validate_filter_body(raw: Any, policy: FilterPolicy, path: str = ROOT_PATH) -> None:
    match shape_of(raw, path):
        case GroupShape(operator=operator, children=children):
            for index, child in enumerate(children):
                validate_filter_body(child, policy, f"{path}.{operator}[{index}]")
        case LeafShape() as leaf:
            validate_leaf(leaf, policy, path)


def validate_leaf(leaf: LeafShape, policy: FilterPolicy, path: str) -> None:
    field_policy = policy.get(leaf.field_name)
    if field_policy is None:
        raise PolicyViolationError(
            f"Field {leaf.field_name!r} is not filterable on this resource",
            path=f"{path}.{FIELD_NAME_KEY}",
        )

    if leaf.operator not in KNOWN_OPERATORS:
        raise InvalidOperationError(
            f"Unknown operator {leaf.operator!r}",
            path=f"{path}.{OPERATOR_KEY}",
        )

    field_policy.check_valid_value(leaf.as_node(), path=path)
