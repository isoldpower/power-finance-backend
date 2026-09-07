import re
from enum import IntEnum, StrEnum


class MoneySettings(IntEnum):
    MAX_INTEGER_DIGITS = 18


class MoneyKey(StrEnum):
    AMOUNT = "amount"
    CURRENCY = "currency"


class AmountSymbol(StrEnum):
    MINUS_SIGN = "-"
    DECIMAL_POINT = "."


CANONICAL_AMOUNT = re.compile(r"^-?(0|[1-9][0-9]*)(\.[0-9]+)?$")
