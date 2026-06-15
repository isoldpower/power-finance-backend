from abc import ABC, abstractmethod
from typing import Any

from django.db.models import Q


class TreeNode(ABC):
    """A node in a parsed filter tree, resolvable to either a Django ORM
    predicate or an Elasticsearch query clause."""

    @abstractmethod
    def resolve(self) -> Q: ...

    @abstractmethod
    def resolve_es(self) -> dict[str, Any]: ...
