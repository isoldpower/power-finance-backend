from decimal import Decimal

from .contracts import ConversationActivity, Overview, Signal, SignalTone

SPEND_LABEL = "Spend vs last month"
UNCATEGORISED_LABEL = "Uncategorised"
RECORDED_LABEL = "Recorded this month"

NO_BASELINE = "no baseline yet"
NOTHING_SPENT = "nothing yet"

BASE_PROMPTS = (
    "Where did my money go last month?",
    "What am I spending the most on?",
)
UNCATEGORISED_PROMPT = "Which transactions still need a category?"
FIRST_TRANSACTION_PROMPT = "How do I record my first transaction?"


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

    change = (
        (activity.spend_this_month - activity.spend_last_month) / activity.spend_last_month
    ) * Decimal(100)
    rounded = int(change.to_integral_value())

    return Signal(
        label=SPEND_LABEL,
        value=f"{rounded:+d}%",
        tone=(
            SignalTone.NEGATIVE
            if rounded > 0
            else SignalTone.POSITIVE
            if rounded < 0
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
