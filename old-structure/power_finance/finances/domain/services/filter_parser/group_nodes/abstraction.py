from abc import abstractmethod, ABC
from typing import Any

from django.db.models import Q

from ....entities import GroupOperator
from ..abstraction import TreeNode, FilterTreeNode


class GroupTreeNode(TreeNode):
    children: list[TreeNode]

    def __init__(
            self,
            children: list[TreeNode] = None,
            **kwargs
    ):
        super().__init__(**kwargs)
        self.children = children

    @classmethod
    @abstractmethod
    def is_related(cls, operator: str) -> bool:
        raise NotImplementedError()

    @abstractmethod
    def resolve(self) -> Q:
        raise NotImplementedError()


class FilterGroupTreeNode(FilterTreeNode, GroupTreeNode):
    def __init__(
            self,
            children: list[TreeNode]
    ):
        super().__init__(children=children)

    @classmethod
    @abstractmethod
    def is_related(cls, operator: str) -> bool:
        raise NotImplementedError()

    @abstractmethod
    def resolve(self) -> Q:
        raise NotImplementedError()


class GroupNodeBuilder(ABC):
    @abstractmethod
    def get_related_group(
            self,
            children: list[TreeNode],
            operator: GroupOperator,
    ) -> GroupTreeNode:
        raise NotImplementedError()

    @abstractmethod
    def validate(self, raw: dict[str, Any]) -> bool:
        raise NotImplementedError()

    @abstractmethod
    def is_group(self, raw: dict[str, Any]) -> bool:
        raise NotImplementedError()

    @abstractmethod
    def parse_raw(
            self,
            raw_value: dict[str, Any]
    ) -> tuple[GroupOperator, list[dict[str, Any]]]:
        raise NotImplementedError()
