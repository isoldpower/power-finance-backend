from datetime import UTC, datetime, timedelta
from decimal import Decimal

from data_read_core.shared.exchange_rates import RateSnapshot

NOW = datetime(2026, 8, 20, 12, 0, tzinfo=UTC)


def snapshot(fetched_at: datetime = NOW) -> RateSnapshot:
    return RateSnapshot(
        base="USD",
        rates={"USD": Decimal("1"), "EUR": Decimal("0.9"), "RUB": Decimal("81.5")},
        fetched_at=fetched_at,
    )


def test_rate_lookup_is_case_insensitive():
    assert snapshot().rate_to("eur") == Decimal("0.9")


def test_an_absent_code_is_none_rather_than_a_guess():
    assert snapshot().rate_to("XYZ") is None


def test_freshness_is_measured_against_the_feed_timestamp():
    day_old = snapshot(NOW - timedelta(days=1))

    assert day_old.is_fresh(timedelta(days=2), now=NOW) is True
    assert day_old.is_fresh(timedelta(hours=1), now=NOW) is False


def test_only_narrows_the_map_and_keeps_the_timestamp():
    narrowed = snapshot().only(["eur"])

    assert narrowed.rates == {"EUR": Decimal("0.9")}
    assert narrowed.fetched_at == NOW
    assert narrowed.base == "USD"


def test_cache_round_trip_keeps_decimals_exact():
    """Rates go through JSON, so they must never be serialised as floats."""

    restored = RateSnapshot.from_cache(snapshot().to_cache())

    assert restored == snapshot()
    assert restored.rate_to("RUB") == Decimal("81.5")
