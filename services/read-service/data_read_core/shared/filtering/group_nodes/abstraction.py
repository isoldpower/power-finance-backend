from abc import ABC, abstractmethod
from typing import Any, ClassVar

from ..abstraction import TreeNode
from ..entities import GroupOperator


class GroupTreeNode(TreeNode):
    """A boolean combination (and/or) of child nodes."""

    operator: ClassVar[GroupOperator]

    def __init__(self, children: list[TreeNode]) -> None:
        self._children = children

    @classmethod
    def is_related(cls, operator: GroupOperator) -> bool:
        return operator is cls.operator


class GroupNodeBuilder(ABC):
    @abstractmethod
    def is_group(self, raw: dict[str, Any]) -> bool: ...

    @abstractmethod
    def validate(self, raw: dict[str, Any], path: str) -> None: ...

    @abstractmethod
    def parse_raw(
        self, raw: dict[str, Any], path: str
    ) -> tuple[GroupOperator, list[dict[str, Any]]]: ...

    @abstractmethod
    def get_related_group(
        self, children: list[TreeNode], operator: GroupOperator, path: str
    ) -> GroupTreeNode: ...
