from enum import IntEnum, StrEnum


class ParamsList(StrEnum):
    STATUS = "status"
    SOURCE = "source"
    SEVERITY = "severity"
    ENABLED = "enabled"


class MoneySettings(IntEnum):
    DEFAULT_DECIMALS = 2
