from abc import abstractmethod, ABC
from typing import Any

from django.db.models import Q

from ....entities import ComparisonOperator, FilterFieldPolicy, FieldFilter
from ..abstraction import TreeNode, FilterTreeNode


class LeafTreeNode(TreeNode):
    field_name: str
    value: str
    operator: ComparisonOperator

    def __init__(self, value: FieldFilter):
        self.field_filter = value
        self.field_name = value.field_name
        self.value = value.value
        self.operator = value.operator

    @classmethod
    @abstractmethod
    def is_related(cls, value: FieldFilter) -> bool:
        raise NotImplementedError()

    @abstractmethod
    def resolve(self) -> Q:
        raise NotImplementedError()

    @abstractmethod
    def resolve_sql(self) -> tuple[str, dict]:
        raise NotImplementedError()


class FilterLeafTreeNode(LeafTreeNode, FilterTreeNode):
    policy: FilterFieldPolicy

    def __init__(self, value: FieldFilter, policy: FilterFieldPolicy):
        LeafTreeNode.__init__(self, value)
        FilterTreeNode.__init__(self)

        self.policy = policy

    @abstractmethod
    def resolve(self) -> Q:
        raise NotImplementedError()

    @abstractmethod
    def resolve_sql(self) -> tuple[str, dict]:
        raise NotImplementedError()


class LeafNodeBuilder(ABC):
    @abstractmethod
    def get_related_leaf(self, value: FieldFilter) -> LeafTreeNode:
        raise NotImplementedError()

    @abstractmethod
    def is_leaf(self, raw_value: dict[str, Any]) -> bool:
        raise NotImplementedError()
