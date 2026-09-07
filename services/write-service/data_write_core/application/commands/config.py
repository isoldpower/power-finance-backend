from enum import IntEnum, StrEnum


class AggregateType(StrEnum):
    ACTION = "action"
    AUTOMATION = "automation"
    TRANSACTION = "transaction"


class SweepSettings(IntEnum):
    DEFAULT_LIMIT = 200


class TransferLeg(StrEnum):
    WITHDRAWAL = "from"
    DEPOSIT = "to"


class WalletDefaults(StrEnum):
    OPENING_BALANCE_NAME = "Opening balance"


class ActionKind(StrEnum):
    AUTOMATION = "automation"
