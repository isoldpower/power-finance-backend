from decimal import Decimal

from .entities import ConversationActivity, Overview, Signal, SignalTone
from .messages import (
    BASE_PROMPTS,
    FIRST_TRANSACTION_PROMPT,
    NO_BASELINE,
    NOTHING_SPENT,
    RECORDED_LABEL,
    SPEND_LABEL,
    UNCATEGORISED_LABEL,
    UNCATEGORISED_PROMPT,
)


def build_overview(activity: ConversationActivity) -> Overview:
    return Overview(
        signals=(
            _spend_signal(activity),
            _uncategorised_signal(activity),
            _recorded_signal(activity),
        ),
        prompts=_prompts(activity),
    )


def _spend_signal(activity: ConversationActivity) -> Signal:
    if activity.spend_last_month <= 0:
        return Signal(SPEND_LABEL, NO_BASELINE, SignalTone.MUTED)
    if activity.spend_this_month <= 0:
        return Signal(SPEND_LABEL, NOTHING_SPENT, SignalTone.POSITIVE)

    spend_difference = activity.spend_this_month - activity.spend_last_month
    change_percentage = spend_difference / activity.spend_last_month * Decimal(100)
    change_rounded = int(change_percentage.to_integral_value())

    return Signal(
        label=SPEND_LABEL,
        value=f"{change_rounded:+d}%",
        tone=(
            SignalTone.NEGATIVE
            if change_rounded > 0
            else SignalTone.POSITIVE
            if change_rounded < 0
            else SignalTone.MUTED
        ),
    )


def _uncategorised_signal(activity: ConversationActivity) -> Signal:
    return Signal(
        label=UNCATEGORISED_LABEL,
        value=_transactions(activity.uncategorised),
        tone=SignalTone.MUTED,
    )


def _recorded_signal(activity: ConversationActivity) -> Signal:
    return Signal(
        label=RECORDED_LABEL,
        value=_transactions(activity.recorded_this_month),
        tone=SignalTone.MUTED,
    )


def _prompts(activity: ConversationActivity) -> tuple[str, ...]:
    if activity.recorded_this_month == 0 and activity.uncategorised == 0:
        return (
            FIRST_TRANSACTION_PROMPT,
            *BASE_PROMPTS,
        )
    if activity.uncategorised > 0:
        return (
            UNCATEGORISED_PROMPT,
            *BASE_PROMPTS,
        )

    return BASE_PROMPTS


def _transactions(count: int) -> str:
    return f"{count} transaction" if count == 1 else f"{count} transactions"
