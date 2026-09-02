"""What makes a run unique.

The key is what decides whether "again" means anything, so its boundaries are
the behaviour: a daily rule that runs twice in a day is a bug the user sees as a
duplicate transfer.
"""

from datetime import UTC, datetime

from data_write_core.domain.automations import (
    period_bucket,
    transaction_run_key,
    wallet_run_key,
)

WALLET_ID = "11111111-1111-1111-1111-111111111111"


def moment(year: int, month: int, day: int) -> datetime:
    return datetime(year, month, day, 12, tzinfo=UTC)


def test_an_event_rule_is_keyed_by_the_transaction_alone():
    """No period: an event rule fires once per transaction, ever."""

    assert transaction_run_key("abc") == "transaction:abc"


def test_daily_changes_at_the_date_boundary():
    assert period_bucket("daily", moment(2026, 9, 1)) == "2026-09-01"
    assert period_bucket("daily", moment(2026, 9, 2)) != period_bucket("daily", moment(2026, 9, 1))


def test_weekly_uses_the_iso_week_so_the_boundary_is_monday():
    """Rather than "seven days after whenever the rule was written", which
    would make two rules created on different days disagree about the week."""

    monday = moment(2026, 8, 31)
    sunday = moment(2026, 9, 6)
    next_monday = moment(2026, 9, 7)

    assert period_bucket("weekly", monday) == period_bucket("weekly", sunday)
    assert period_bucket("weekly", next_monday) != period_bucket("weekly", monday)


def test_monthly_changes_at_the_month_boundary():
    assert period_bucket("monthly", moment(2026, 9, 30)) == "2026-09"
    assert period_bucket("monthly", moment(2026, 10, 1)) == "2026-10"


def test_a_scheduled_key_names_both_the_subject_and_the_period():
    """Both, because a scheduled rule runs once per WALLET per period — one
    without the other would either skip wallets or repeat months."""

    key = wallet_run_key(WALLET_ID, "monthly", moment(2026, 9, 15))

    assert key == f"wallet:{WALLET_ID}@2026-09"
