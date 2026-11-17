from datetime import timedelta
from decimal import Decimal
from enum import IntEnum, StrEnum
from typing import NamedTuple


class CacheSettings(IntEnum):
    TTL_SECONDS = 60


class CacheSchema(StrEnum):
    VERSION = "s2"


class ReservedTokens(StrEnum):
    UNCATEGORISED = "__none__"
    OTHER = "__other__"


class LedgerSide(StrEnum):
    EXPENSE = "expense"
    INCOME = "income"


class Granularity(StrEnum):
    DAY = "day"
    WEEK = "week"
    MONTH = "month"


class ParamsList(StrEnum):
    SINCE = "since"
    UNTIL = "until"
    CURRENCY = "currency"
    WALLET_ID = "wallet_id"
    TIMEZONE = "timezone"
    CATEGORY = "category"
    GRANULARITY = "granularity"
    TYPE = "type"
    LIMIT = "limit"
    POINTS = "points"
    ORDER = "order"
    NAME = "name"


class Messages(StrEnum):
    UNPARSABLE_DATETIME = "{parameter} must be an ISO-8601 datetime"
    UNTIL_NOT_AFTER_SINCE = "until must be after since"
    WINDOW_TOO_LONG = "The window may cover at most {days} days"
    UNKNOWN_TIMEZONE = "timezone must be an IANA zone name, got {timezone!r}"
    UNKNOWN_WALLET = "Wallet {wallet} does not exist"
    UNKNOWN_CATEGORY = "Transaction category {category} does not exist"
    UNKNOWN_GRANULARITY = "granularity must be one of: {legal}"
    TOO_MANY_BUCKETS = "The window holds more than {maximum} buckets; choose a coarser granularity"
    UNKNOWN_SIDE = "type must be one of: {legal}"
    UNKNOWN_ORDER = "order must be one of: {legal}"
    INTEGER_OUT_OF_RANGE = "{parameter} must be an integer between {minimum} and {maximum}"


class IntegerBounds(NamedTuple):
    parameter: str
    default: int
    minimum: int
    maximum: int


LIST_SEPARATOR = ","
DEFAULT_TIMEZONE = "UTC"
DEFAULT_WINDOW_LENGTH = timedelta(days=30)
MAXIMUM_WINDOW_LENGTH = timedelta(days=5 * 366)
DAY_GRANULARITY_LIMIT = timedelta(days=45)
WEEK_GRANULARITY_LIMIT = timedelta(days=200)
MAXIMUM_BUCKET_COUNT = 400
SECONDS_PER_DAY = 86400

PERCENTAGE_EXPONENT = Decimal("0.01")
HUNDRED = Decimal(100)
ZERO = Decimal(0)
