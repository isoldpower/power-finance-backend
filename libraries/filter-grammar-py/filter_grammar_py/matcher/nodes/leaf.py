from typing import Any

from ...entities import FilterFieldPolicy, FilterPolicy
from ...exceptions import InvalidOperationError, PolicyViolationError
from ...shapes import FIELD_NAME_KEY, OPERATOR_KEY, LeafShape
from ...validator import KNOWN_OPERATORS
from ...value_types import UncomparableValue
from ..node import MatchNode, Record
from ..values import compare


class LeafNode(MatchNode):
    def __init__(
        self,
        field_name: str,
        operator: str,
        expected: Any,
        field_policy: FilterFieldPolicy,
    ) -> None:
        self._field_name = field_name
        self._operator = operator
        self._expected = expected
        self._field_policy = field_policy

    @classmethod
    def build(cls, leaf: LeafShape, policy: FilterPolicy, path: str) -> "LeafNode":
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
        if leaf.operator not in field_policy.allowed_operators:
            raise InvalidOperationError(
                f"Operator {leaf.operator!r} is not permitted on {leaf.field_name!r}",
                path=f"{path}.{OPERATOR_KEY}",
            )

        return cls(leaf.field_name, leaf.operator, leaf.value, field_policy)

    @property
    def field_name(self) -> str:
        return self._field_name

    @property
    def operator(self) -> str:
        return self._operator

    def matches(self, record: Record) -> bool:
        present = record.get(self._field_name)
        if present is None:
            return False

        try:
            return compare(self._operator, present, self._expected, self._field_policy)
        except UncomparableValue:
            return False
