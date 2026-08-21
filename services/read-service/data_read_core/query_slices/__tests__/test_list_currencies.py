import pytest

from data_read_core.query_slices.list_currencies.dtos import ListCurrenciesQuery
from data_read_core.query_slices.list_currencies.http._presenters import present_many
from data_read_core.query_slices.list_currencies.query_handler import (
    ListCurrenciesQueryHandler,
)
from data_read_core.shared.money import CURRENCY_CATALOG
from data_read_core.shared.pagination import CompletePage
from data_read_core.shared.postgres_orm import CurrencyReadModel

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture(autouse=True)
async def _reference_currencies():
    CURRENCY_CATALOG.reset()
    await CurrencyReadModel.objects.abulk_create(
        [
            CurrencyReadModel(code="USD", name="US Dollar", symbol="$", numeric="840", digits=2),
            CurrencyReadModel(code="EUR", name="Euro", symbol="€", numeric="978", digits=2),
            CurrencyReadModel(code="JPY", name="Japanese Yen", symbol="¥", numeric="392", digits=0),
        ],
        ignore_conflicts=True,
    )
    yield
    CURRENCY_CATALOG.reset()


async def test_the_whole_table_is_served_in_code_order():
    fetched = await ListCurrenciesQueryHandler().handle(ListCurrenciesQuery())

    assert [currency.code for currency in fetched.rows] == ["EUR", "JPY", "USD"]
    assert fetched.total == 3


async def test_the_presented_shape_spells_digits_as_decimals():
    fetched = await ListCurrenciesQueryHandler().handle(ListCurrenciesQuery())

    assert present_many(fetched.rows)[1] == {
        "code": "JPY",
        "symbol": "¥",
        "name": "Japanese Yen",
        "decimals": 0,
    }


async def test_the_endpoint_reports_itself_as_unpaginated():
    """The page rules do not apply to a static table fetched once at app load,
    so `limit` and both cursors stay null and the list is always complete."""

    fetched = await ListCurrenciesQueryHandler().handle(ListCurrenciesQuery())

    assert CompletePage(fetched.rows).meta() == {
        "limit": None,
        "total": 3,
        "next_cursor": None,
        "prev_cursor": None,
    }
