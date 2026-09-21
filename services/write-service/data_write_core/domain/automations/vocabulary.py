from enum import StrEnum

from filter_grammar_py import FilterResource


class TriggerType(StrEnum):
    EVENT = "event"
    SCHEDULE = "schedule"


class TriggerEvent(StrEnum):
    TRANSACTION_CREATED = "transaction.created"
    TRANSACTION_UPDATED = "transaction.updated"


class TriggerSchedule(StrEnum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class SubjectType(StrEnum):
    TRANSACTION = "transaction"
    WALLET = "wallet"


class EffectType(StrEnum):
    SET_CATEGORY = "set_category"
    NOTIFY = "notify"
    RAISE_ACTION = "raise_action"
    TRANSFER = "transfer"


class Severity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


SUBJECT_BY_TRIGGER_TYPE: dict[str, str] = {
    TriggerType.EVENT: FilterResource.TRANSACTIONS,
    TriggerType.SCHEDULE: FilterResource.WALLETS,
}

TRIGGER_TYPE_CHOICES: list[str] = [member.value for member in TriggerType]
TRIGGER_EVENT_CHOICES: list[str] = [member.value for member in TriggerEvent]
TRIGGER_SCHEDULE_CHOICES: list[str] = [member.value for member in TriggerSchedule]
EFFECT_TYPE_CHOICES: list[str] = [member.value for member in EffectType]


def subject_of(trigger_type: str) -> str:
    return SUBJECT_BY_TRIGGER_TYPE[trigger_type]
