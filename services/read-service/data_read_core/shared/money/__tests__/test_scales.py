import pytest

from data_read_core.shared.http_contract import UnsupportedCurrency
from data_read_core.shared.money import CURRENCY_SCALES, amount_at_scale
from data_read_core.shared.postgres_orm import CurrencyReadModel

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture(autouse=True)
async def _reference_currencies():
    """Seed the rows this test needs: `transaction=True` truncates between tests
    without replaying the data migration that seeds them."""

    CURRENCY_SCALES.reset()
    await CurrencyReadModel.objects.abulk_create(
        [
            CurrencyReadModel(code="USD", name="US Dollar", numeric="840", digits=2),
            CurrencyReadModel(code="JPY", name="Japanese Yen", numeric="392", digits=0),
        ],
        ignore_conflicts=True,
    )
    yield
    CURRENCY_SCALES.reset()


async def test_scales_come_from_the_seeded_reference_table():
    assert await CURRENCY_SCALES.decimals_for("USD") == 2
    assert await CURRENCY_SCALES.decimals_for("JPY") == 0


async def test_currency_code_is_case_insensitive():
    assert await CURRENCY_SCALES.decimals_for("usd") == 2


async def test_unknown_currency_in_a_request_is_rejected():
    with pytest.raises(UnsupportedCurrency):
        await CURRENCY_SCALES.decimals_for("XYZ")


async def test_unknown_currency_already_in_the_store_degrades_to_the_default():
    """Unreadable reference data must not make an otherwise valid row
    unreadable."""

    assert await CURRENCY_SCALES.decimals_or_default("XYZ") == 2
    assert await CURRENCY_SCALES.decimals_or_default(None) == 2


async def test_the_same_code_path_scales_both_currencies():
    assert await amount_at_scale("50", "USD") == "50.00"
    assert await amount_at_scale("90", "JPY") == "90"
