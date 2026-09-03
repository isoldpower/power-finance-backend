"""What the panel's headline signals say, and when."""

from decimal import Decimal

from ..contracts import ConversationActivity, SignalTone
from ..overview_builder import (
    FIRST_TRANSACTION_PROMPT,
    NO_BASELINE,
    NOTHING_SPENT,
    RECORDED_LABEL,
    SPEND_LABEL,
    UNCATEGORISED_LABEL,
    UNCATEGORISED_PROMPT,
    build_overview,
)


def _activity(
    *,
    this_month: str = "0",
    last_month: str = "0",
    uncategorised: int = 0,
    recorded: int = 0,
) -> ConversationActivity:
    return ConversationActivity(
        spend_currency="USD",
        spend_this_month=Decimal(this_month),
        spend_last_month=Decimal(last_month),
        uncategorised=uncategorised,
        recorded_this_month=recorded,
    )


def _signal(overview, label: str):
    return next(signal for signal in overview.signals if signal.label == label)


def test_spending_more_than_last_month_reads_negative():
    overview = build_overview(_activity(this_month="138", last_month="100"))

    spend = _signal(overview, SPEND_LABEL)
    assert spend.value == "+38%"
    assert spend.tone is SignalTone.NEGATIVE


def test_spending_less_reads_positive():
    spend = _signal(build_overview(_activity(this_month="80", last_month="100")), SPEND_LABEL)

    assert spend.value == "-20%"
    assert spend.tone is SignalTone.POSITIVE


def test_spending_the_same_is_neither_good_nor_bad():
    spend = _signal(build_overview(_activity(this_month="100", last_month="100")), SPEND_LABEL)

    assert spend.value == "+0%"
    assert spend.tone is SignalTone.MUTED


def test_a_first_month_has_nothing_to_compare_against():
    """A percentage against zero is not a large number, it is undefined."""

    spend = _signal(build_overview(_activity(this_month="100")), SPEND_LABEL)

    assert spend.value == NO_BASELINE
    assert spend.tone is SignalTone.MUTED


def test_a_month_with_no_spending_says_so():
    spend = _signal(build_overview(_activity(last_month="100")), SPEND_LABEL)

    assert spend.value == NOTHING_SPENT
    assert spend.tone is SignalTone.POSITIVE


def test_counts_are_written_as_display_text():
    """`value` is a preformatted string, not a number a client re-renders."""

    overview = build_overview(_activity(uncategorised=3, recorded=12))

    assert _signal(overview, UNCATEGORISED_LABEL).value == "3 transactions"
    assert _signal(overview, RECORDED_LABEL).value == "12 transactions"


def test_a_single_transaction_is_not_pluralised():
    assert _signal(build_overview(_activity(uncategorised=1)), UNCATEGORISED_LABEL).value == (
        "1 transaction"
    )


def test_uncategorised_work_is_suggested_as_a_prompt():
    """Prompts are input to the conversation exactly as if the user had typed
    them, so they should name something worth asking about."""

    overview = build_overview(_activity(uncategorised=3, recorded=5))

    assert overview.prompts[0] == UNCATEGORISED_PROMPT


def test_an_empty_ledger_is_offered_somewhere_to_start():
    overview = build_overview(_activity())

    assert overview.prompts[0] == FIRST_TRANSACTION_PROMPT


def test_a_tidy_month_gets_the_plain_suggestions():
    overview = build_overview(_activity(recorded=5))

    assert UNCATEGORISED_PROMPT not in overview.prompts
    assert FIRST_TRANSACTION_PROMPT not in overview.prompts


def test_both_collections_are_small_and_complete():
    overview = build_overview(_activity(this_month="1", last_month="1", recorded=1))

    assert len(overview.signals) == 3
    assert overview.prompts
