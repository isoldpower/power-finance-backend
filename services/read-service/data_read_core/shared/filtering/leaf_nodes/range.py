from ..entities import ComparisonOperator
from .abstraction import RangeLeafTreeNode


class GreaterLeafTreeNode(RangeLeafTreeNode):
    operator = ComparisonOperator.Greater
    query_suffix = "gt"
    es_operator = "gt"


class GreaterEqualLeafTreeNode(RangeLeafTreeNode):
    operator = ComparisonOperator.GreaterEqual
    query_suffix = "gte"
    es_operator = "gte"


class LessLeafTreeNode(RangeLeafTreeNode):
    operator = ComparisonOperator.Less
    query_suffix = "lt"
    es_operator = "lt"


class LessEqualLeafTreeNode(RangeLeafTreeNode):
    operator = ComparisonOperator.LessEqual
    query_suffix = "lte"
    es_operator = "lte"
