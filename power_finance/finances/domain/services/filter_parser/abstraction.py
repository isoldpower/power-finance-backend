from abc import ABC, abstractmethod
from django.db.models import Q


class TreeNode(ABC):
    @abstractmethod
    def resolve(self) -> Q:
        raise NotImplementedError()


class FilterTreeNode(TreeNode):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @abstractmethod
    def resolve(self) -> Q:
        raise NotImplementedError()