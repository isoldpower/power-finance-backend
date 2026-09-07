from enum import StrEnum


class OrderingFormat(StrEnum):
    SIGNATURE_SEPARATOR = ","
    DESCENDING_PREFIX = "-"
    ASCENDING_PREFIX = ""
    DJANGO_LOOKUP_SEPARATOR = "__"


class KeysetLookup(StrEnum):
    LESS_THAN = "lt"
    GREATER_THAN = "gt"
