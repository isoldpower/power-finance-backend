from enum import Enum


class ComparisonOperator(str, Enum):
    Equal = "eq"
    NotEqual = "neq"
    IContains = "icontains"
    Contains = "contains"
    GreaterEqual = "gte"
    LessEqual = "lte"
    Greater = "gt"
    Less = "lt"
    In = "in"


class GroupOperator(str, Enum):
    And = "and"
    Or = "or"


class TypeVariant(str, Enum):
    INTEGER = "int"
    FLOAT = "float"
    DECIMAL = "decimal"
    STRING = "str"
    BOOLEAN = "bool"
    DATETIME = "datetime"
    UUID = "uuid"
