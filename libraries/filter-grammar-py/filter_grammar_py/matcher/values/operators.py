from collections.abc import Callable
from typing import Any

from ...vocabulary import ComparisonOperator

OPERATORS: dict[str, Callable[[Any, Any], bool]] = {
    ComparisonOperator.Equal: lambda left, right: bool(left == right),
    ComparisonOperator.NotEqual: lambda left, right: bool(left != right),
    ComparisonOperator.Greater: lambda left, right: bool(left > right),
    ComparisonOperator.GreaterEqual: lambda left, right: bool(left >= right),
    ComparisonOperator.Less: lambda left, right: bool(left < right),
    ComparisonOperator.LessEqual: lambda left, right: bool(left <= right),
    ComparisonOperator.Contains: lambda left, right: str(right) in str(left),
    ComparisonOperator.IContains: lambda left, right: str(right).lower() in str(left).lower(),
}
