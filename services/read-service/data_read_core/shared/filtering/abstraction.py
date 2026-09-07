from abc import ABC, abstractmethod
from typing import Any

from django.db.models import Q


class TreeNode(ABC):
    @abstractmethod
    def resolve(self) -> Q: ...

    @abstractmethod
    def resolve_es(self) -> dict[str, Any]: ...
