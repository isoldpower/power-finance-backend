from typing import Any

from django.db.models import Q

from ..entities import ComparisonOperator
from .abstraction import LeafTreeNode


class InLeafTreeNode(LeafTreeNode):
    operator = ComparisonOperator.In

    def resolve(self) -> Q:
        return Q(**{f"{self.model_lookup}__in": self.value})

    def resolve_es(self) -> dict[str, Any]:
        values = self.value if isinstance(self.value, list) else [self.value]
        return {"terms": {self.es_field: values}}
