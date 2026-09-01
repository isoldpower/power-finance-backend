"""Folding many currencies into the one a metrics response reports in."""

from decimal import Decimal

from data_read_core.shared.metrics import MoneyFolder


class StubRates:
    """Counts lookups, because the point of the folder is that a series of a
    hundred buckets costs the same rates as a single one."""

    def __init__(self, rates: dict[tuple[str, str], Decimal]):
        self._rates = rates
        self.asked: list[tuple[str, str]] = []

    async def rate_between(self, base: str, quote: str):
        self.asked.append((base, quote))
        return self._rates[(base, quote)], None


def folder(rates: StubRates, target: str = "USD") -> MoneyFolder:
    return MoneyFolder(target, rate_service=rates)


async def test_the_reporting_currency_needs_no_rate():
    rates = StubRates({})

    total = await folder(rates).fold({"USD": Decimal("10.00")})

    assert total == Decimal("10.00")
    assert rates.asked == []


async def test_other_currencies_are_converted_before_they_are_added():
    rates = StubRates({("JPY", "USD"): Decimal("0.0066")})

    total = await folder(rates).fold({"USD": Decimal("10.00"), "JPY": Decimal("1000")})

    assert total == Decimal("10.00") + Decimal("1000") * Decimal("0.0066")


async def test_a_rate_is_resolved_once_and_reused_across_folds():
    rates = StubRates({("JPY", "USD"): Decimal("0.0066")})
    reused = folder(rates)

    for _ in range(5):
        await reused.fold({"JPY": Decimal("100")})

    assert rates.asked == [("JPY", "USD")]


async def test_a_blank_currency_counts_at_face_value():
    """A blank code means the projection never learned the denomination.
    Dropping it would silently understate every figure it appears in."""

    rates = StubRates({})

    total = await folder(rates).fold({"": Decimal("7.00")})

    assert total == Decimal("7.00")
    assert rates.asked == []


async def test_folding_does_not_round():
    """Rounding is the presenter's job, once. Quantizing here would compound
    the error across every bucket of a series."""

    rates = StubRates({("EUR", "USD"): Decimal("1.111111")})

    total = await folder(rates).fold({"EUR": Decimal("1")})

    assert total == Decimal("1.111111")


async def test_prepare_resolves_every_rate_up_front():
    """So a partially folded series cannot fail halfway and leave some buckets
    converted and others not."""

    rates = StubRates(
        {("JPY", "USD"): Decimal("0.0066"), ("EUR", "USD"): Decimal("1.1")},
    )
    prepared = folder(rates)

    await prepared.prepare(["JPY", "EUR", "USD", "JPY"])

    assert sorted(rates.asked) == [("EUR", "USD"), ("JPY", "USD")]
