from collections.abc import Sequence

from ...vocabulary import GroupOperator
from ..node import MatchNode, Record


class GroupNode(MatchNode):
    def __init__(self, operator: str, children: Sequence[MatchNode]) -> None:
        self._operator = operator
        self._children = tuple(children)

    @property
    def operator(self) -> str:
        return self._operator

    @property
    def children(self) -> tuple[MatchNode, ...]:
        return self._children

    def matches(self, record: Record) -> bool:
        if self._operator == GroupOperator.And:
            return all(child.matches(record) for child in self._children)

        return any(child.matches(record) for child in self._children)
