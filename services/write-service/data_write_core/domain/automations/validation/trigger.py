from typing import Any

from filter_grammar_py import (
    FilterParseError,
    policy_for,
    validate_filter_body,
)

from ..vocabulary import (
    TriggerEvent,
    TriggerSchedule,
    TriggerType,
    subject_of,
)
from .refusal import (
    FILTER_BODY_PATH,
    INVALID,
    REQUIRED,
    TRIGGER_FIELD_CONFLICT,
    TRIGGER_PATH,
    AutomationRefusal,
)


def validate_trigger(trigger: dict[str, Any]) -> None:
    trigger_type = trigger.get("type")
    if trigger_type not in list(TriggerType):
        raise AutomationRefusal(
            path=f"{TRIGGER_PATH}.type",
            detail_code=INVALID,
            reason=f"Unknown trigger type. Legal values: {', '.join(TriggerType)}.",
        )

    _refuse_the_wrong_selector(trigger, trigger_type)
    _validate_selector(trigger, trigger_type)
    _validate_filter_body(trigger, trigger_type)


def _refuse_the_wrong_selector(trigger: dict[str, Any], trigger_type: str) -> None:
    unwanted = "schedule" if trigger_type == TriggerType.EVENT else "event"
    if trigger.get(unwanted) is not None:
        raise AutomationRefusal(
            path=f"{TRIGGER_PATH}.{unwanted}",
            detail_code=TRIGGER_FIELD_CONFLICT,
            reason=f"`{unwanted}` does not belong to a `{trigger_type}` trigger.",
        )


def _validate_selector(trigger: dict[str, Any], trigger_type: str) -> None:
    if trigger_type == TriggerType.EVENT:
        _require_member(
            trigger.get("event"),
            TriggerEvent,
            f"{TRIGGER_PATH}.event",
        )
    else:
        _require_member(
            trigger.get("schedule"),
            TriggerSchedule,
            f"{TRIGGER_PATH}.schedule",
        )


def _require_member(value: Any, vocabulary: Any, path: str) -> None:
    if value not in list(vocabulary):
        raise AutomationRefusal(
            path=path,
            detail_code=INVALID if value else REQUIRED,
            reason=f"Legal values: {', '.join(vocabulary)}.",
        )


def _validate_filter_body(trigger: dict[str, Any], trigger_type: str) -> None:
    filter_body = trigger.get("filter_body")
    if filter_body is None:
        return

    try:
        validate_filter_body(
            filter_body,
            policy_for(subject_of(trigger_type)),
            FILTER_BODY_PATH,
        )
    except FilterParseError as error:
        raise AutomationRefusal(
            path=error.path,
            detail_code=error.detail_code,
            reason=error.reason,
        ) from error
