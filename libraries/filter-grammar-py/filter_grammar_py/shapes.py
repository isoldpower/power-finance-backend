from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from .entities import GroupOperator
from .exceptions import (
    InvalidGroupChildrenError,
    InvalidGroupingError,
    InvalidStructureError,
    UnknownNodeError,
)

FIELD_NAME_KEY = "field_name"
OPERATOR_KEY = "operator"
VALUE_KEY = "value"

LEAF_KEYS = frozenset({FIELD_NAME_KEY, OPERATOR_KEY, VALUE_KEY})
GROUP_KEYS = frozenset(member.value for member in GroupOperator)


@dataclass(frozen=True)
class GroupShape:
    operator: str
    children: tuple[Any, ...]


@dataclass(frozen=True)
class LeafShape:
    field_name: Any
    operator: Any
    value: Any

    def as_node(self) -> dict[str, Any]:
        return {
            FIELD_NAME_KEY: self.field_name,
            OPERATOR_KEY: self.operator,
            VALUE_KEY: self.value,
        }


NodeShape = GroupShape | LeafShape


def shape_of(raw: Any, path: str) -> NodeShape:
    match raw:
        case {**node} if GROUP_KEYS & node.keys():
            return _group_shape(node, path)
        case {**node} if LEAF_KEYS & node.keys():
            return _leaf_shape(node, path)
        case {}:
            raise UnknownNodeError("Node is neither a valid group nor a valid leaf", path=path)
        case _:
            raise InvalidStructureError(
                f"Filter node must be an object, got {type(raw).__name__}",
                path=path,
            )


def _group_shape(raw: Mapping[Any, Any], path: str) -> GroupShape:
    match raw:
        case {"and": [_, *_] as children} if len(raw) == 1:
            return GroupShape(GroupOperator.And.value, tuple(children))
        case {"or": [_, *_] as children} if len(raw) == 1:
            return GroupShape(GroupOperator.Or.value, tuple(children))
        case _ if len(raw) != 1:
            raise InvalidGroupingError(
                "A group node carries exactly one of `and` / `or` and nothing else",
                path=path,
            )
        case _:
            raise InvalidGroupChildrenError(
                f"`{next(iter(GROUP_KEYS & raw.keys()))}` must be a non-empty array of nodes",
                path=path,
            )


def _leaf_shape(raw: Mapping[Any, Any], path: str) -> LeafShape:
    match raw:
        case {"field_name": field_name, "operator": operator, "value": value}:
            return LeafShape(field_name, operator, value)
        case _:
            raise InvalidStructureError(
                f"Leaf node is missing {', '.join(sorted(LEAF_KEYS - raw.keys()))}",
                path=path,
            )
