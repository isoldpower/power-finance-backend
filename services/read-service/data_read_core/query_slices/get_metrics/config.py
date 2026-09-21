from decimal import Decimal
from enum import IntEnum, StrEnum

from data_read_core.shared.postgres_orm import AccountGroups


class CacheSettings(IntEnum):
    TTL_SECONDS = 60


class CacheSchema(StrEnum):
    VERSION = "s1"


class Messages(StrEnum):
    NOT_A_BOOLEAN = "{parameter} must be a boolean ({legal})"
    IDENTITY_DRIFT = "Assets do not equal liabilities plus equity; the chart is off by {drift}."
    UNBALANCED_DISPATCH = (
        "{count} transaction(s) were posted with legs that did not agree, most often "
        "because the two sides landed in different currencies."
    )


TRUTH_STATEMENTS = {"1", "true", "yes", "on"}
FALSE_STATEMENTS = {"0", "false", "no", "off"}

COMMENT_SEPARATOR = " "
PERCENTAGE_EXPONENT = Decimal("0.01")
ZERO = Decimal(0)

EMPTY_GROUPS: dict[str, Decimal] = {group.value: ZERO for group in AccountGroups}


class Section(StrEnum):
    BALANCE = "balance"
    NET_WORTH = "net-worth"
    CASH_FLOW = "cash-flow"

    @property
    def key(self) -> str:
        return self.value.replace("-", "_")


ALL_SECTIONS = tuple(Section)
