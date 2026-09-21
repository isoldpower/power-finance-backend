from filter_grammar_py import ComparisonOperator

from .abstraction import WildcardLeafTreeNode


class ContainsLeafTreeNode(WildcardLeafTreeNode):
    operator = ComparisonOperator.Contains
    query_suffix = "contains"
    case_insensitive = False


class IContainsLeafTreeNode(WildcardLeafTreeNode):
    operator = ComparisonOperator.IContains
    query_suffix = "icontains"
    case_insensitive = True
