from decimal import Decimal
from enum import IntEnum, StrEnum

from data_read_core.shared.postgres_orm import AccountGroups


class CacheSettings(IntEnum):
    TTL_SECONDS = 300


class CacheSchema(StrEnum):
    VERSION = "s2"


class ParamsList(StrEnum):
    LOWBAR = "lowbar"


class GroupFilter(StrEnum):
    ALL = "all"


GROUP_CHOICES = (str(GroupFilter.ALL), *(group.value for group in AccountGroups))

BOOK_EXPONENT = Decimal("0.01")
