import json
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from urllib.parse import urlencode

import pytest
from django.contrib.auth import get_user_model
from django.test import AsyncClient

from data_read_core.shared.exchange_rates import get_rate_service
from data_read_core.shared.money import CURRENCY_CATALOG
from data_read_core.shared.postgres_orm import (
    NO_CHAIN_SENTINEL,
    CurrencyReadModel,
    MoneyContainers,
    TransactionReadModel,
    WalletReadModel,
)
from data_read_core.shared.redis_cache import get_redis

from .category_fixtures import owned_category

pytestmark = pytest.mark.django_db(transaction=True)

EXTERNAL_USER_ID = "user_analytics"
OTHER_USER_ID = "user_other_analytics"
AUTH_HEADERS = {"X-User-Id": EXTERNAL_USER_ID}
ANALYTICS = "/api/v1/analytics"

CASH_WALLET_ID = uuid.UUID("aaaaaaaa-0000-0000-0000-000000000001")
EURO_WALLET_ID = uuid.UUID("aaaaaaaa-0000-0000-0000-000000000002")
CLOSED_WALLET_ID = uuid.UUID("aaaaaaaa-0000-0000-0000-000000000003")
FOREIGN_WALLET_ID = uuid.UUID("aaaaaaaa-0000-0000-0000-000000000004")
FRESH_WALLET_ID = uuid.UUID("aaaaaaaa-0000-0000-0000-000000000005")
GOAL_ID = uuid.UUID("aaaaaaaa-0000-0000-0000-000000000006")

WINDOW = {"since": "2026-03-01T00:00:00Z", "until": "2026-03-08T00:00:00Z"}

CACHE_PREFIXES = (
    "read:analytics:*",
    "ver:transactions:*",
    "ver:wallets:*",
    "read:rates:*",
)


def as_user(endpoint: str, **parameters):
    query_string = urlencode({**WINDOW, **parameters})
    return AsyncClient().get(f"{ANALYTICS}/{endpoint}?{query_string}", headers=AUTH_HEADERS)


def body_of(response) -> dict:
    return json.loads(response.content)


def amount_of(money: dict) -> str:
    return money["amount"]


def name_of(category: dict | None) -> str | None:
    return category["name"] if category is not None else None


async def owner_category_id(name: str) -> str:
    owner = await get_user_model().objects.aget(username=EXTERNAL_USER_ID)
    return str((await owned_category(owner.id, "transaction", name)).id)


@pytest.fixture(autouse=True)
async def _empty_cache():
    async def clear() -> None:
        get_rate_service.cache_clear()
        get_redis.cache_clear()
        redis = get_redis()
        for pattern in CACHE_PREFIXES:
            async for key in redis.scan_iter(match=pattern):
                await redis.delete(key)

    await clear()
    yield
    await clear()
    await get_redis().aclose()
    get_rate_service.cache_clear()
    get_redis.cache_clear()


@pytest.fixture(autouse=True)
async def _ledger():
    CURRENCY_CATALOG.reset()
    owner = await get_user_model().objects.acreate(username=EXTERNAL_USER_ID)
    stranger = await get_user_model().objects.acreate(username=OTHER_USER_ID)
    await CurrencyReadModel.objects.abulk_create(
        [
            CurrencyReadModel(code="USD", name="US Dollar", symbol="$", numeric="840", digits=2),
            CurrencyReadModel(code="EUR", name="Euro", symbol="€", numeric="978", digits=2),
            CurrencyReadModel(code="JPY", name="Yen", symbol="¥", numeric="392", digits=0),
        ],
        ignore_conflicts=True,
    )
    await _wallet(CASH_WALLET_ID, owner.id, "Cash", "USD", favorite=True)
    await _wallet(EURO_WALLET_ID, owner.id, "Euro", "EUR")
    await _wallet(CLOSED_WALLET_ID, owner.id, "Closed", "USD", deleted=True)
    await _wallet(FOREIGN_WALLET_ID, stranger.id, "Theirs", "USD")
    await _wallet(FRESH_WALLET_ID, owner.id, "Fresh", "USD")

    transfer_chain = uuid.uuid4()
    await _transaction(
        owner.id,
        CASH_WALLET_ID,
        "1000.00",
        "USD",
        "Opening balance",
        None,
        _at(2, 1, 8),
        opening=True,
    )
    await _transaction(
        owner.id,
        FRESH_WALLET_ID,
        "250.00",
        "USD",
        "Opening balance",
        None,
        _at(3, 3, 12),
        opening=True,
    )
    await _transaction(owner.id, CASH_WALLET_ID, "500.00", "USD", "Salary", "Salary", _at(3, 2, 9))
    await _transaction(
        owner.id, CASH_WALLET_ID, "-100.00", "USD", "Corner Market", "Groceries", _at(3, 3, 18)
    )
    await _transaction(
        owner.id, CASH_WALLET_ID, "-50.00", "USD", " corner market ", "Groceries", _at(3, 5, 18)
    )
    await _transaction(owner.id, CASH_WALLET_ID, "-30.00", "USD", "Cafe", None, _at(3, 5, 12))
    await _transaction(owner.id, EURO_WALLET_ID, "-108.00", "EUR", "Rent", "Rent", _at(3, 4, 10))
    await _transaction(
        owner.id, CASH_WALLET_ID, "-200.00", "USD", "Move", None, _at(3, 6, 8), chain=transfer_chain
    )
    await _transaction(
        owner.id, EURO_WALLET_ID, "180.00", "EUR", "Move", None, _at(3, 6, 8), chain=transfer_chain
    )
    await _transaction(
        owner.id, CASH_WALLET_ID, "-999.00", "USD", "Gone", "Groceries", _at(3, 3, 9), deleted=True
    )
    await _transaction(owner.id, CLOSED_WALLET_ID, "-77.00", "USD", "Old", "Old", _at(3, 3, 9))
    await _transaction(
        owner.id, CASH_WALLET_ID, "-40.00", "USD", "Corner Market", "Groceries", _at(2, 25, 9)
    )
    await _transaction(stranger.id, FOREIGN_WALLET_ID, "-5000.00", "USD", "X", "X", _at(3, 3, 9))
    yield
    CURRENCY_CATALOG.reset()


def _at(month: int, day: int, hour: int) -> datetime:
    return datetime(2026, month, day, hour, tzinfo=UTC)


async def _wallet(
    wallet_id: uuid.UUID,
    user_id: int,
    title: str,
    currency: str,
    *,
    favorite: bool = False,
    deleted: bool = False,
) -> None:
    await WalletReadModel.objects.acreate(
        id=wallet_id,
        user_id=user_id,
        title=title,
        currency_code=currency,
        color="#112233",
        favorite=favorite,
        created_at=_at(1, 1, 0),
        deleted_at=_at(1, 2, 0) if deleted else None,
    )


async def _transaction(
    user_id: int,
    wallet_id: uuid.UUID,
    amount: str,
    currency: str,
    name: str,
    category: str | None,
    created_at: datetime,
    *,
    chain: uuid.UUID | None = None,
    deleted: bool = False,
    opening: bool = False,
    container_kind: str = MoneyContainers.WALLET,
) -> None:
    await TransactionReadModel.objects.acreate(
        id=uuid.uuid4(),
        wallet_id=wallet_id,
        wallet_name="",
        container_kind=container_kind,
        is_opening_balance=opening,
        user_id=user_id,
        amount=Decimal(amount),
        currency_code=currency,
        name=name,
        category=await owned_category(user_id, "transaction", category) if category else None,
        chain_id=chain,
        chain_sort=chain or NO_CHAIN_SENTINEL,
        occurred_at=created_at,
        created_at=created_at,
        deleted_at=created_at if deleted else None,
    )


async def test_dimensions_list_open_wallets_favourites_first_and_the_category_vocabulary():
    payload = body_of(await as_user("dimensions", currency="EUR"))

    assert [wallet["name"] for wallet in payload["data"]["wallets"]] == ["Cash", "Euro", "Fresh"]
    assert payload["data"]["wallets"][1] == {
        "id": str(EURO_WALLET_ID),
        "name": "Euro",
        "color": "#112233",
        "currency": "EUR",
    }
    assert [name_of(category) for category in payload["data"]["categories"]["expense"]] == [
        "Groceries",
        "Rent",
    ]
    assert [name_of(category) for category in payload["data"]["categories"]["income"]] == ["Salary"]
    assert payload["data"]["categories"]["income"][0] == {
        "id": await owner_category_id("Salary"),
        "name": "Salary",
        "is_global": False,
    }
    assert payload["data"]["first_transaction_at"] == "2026-02-01T08:00:00+00:00"
    assert payload["data"]["last_transaction_at"] == "2026-03-06T08:00:00+00:00"
    assert payload["meta"]["currency"] == "EUR"


async def test_overview_excludes_transfers_and_converts_into_the_requested_currency():
    payload = body_of(await as_user("overview", currency="USD"))
    current = payload["data"]["current"]

    assert amount_of(current["inflow"]) == "500.00"
    assert amount_of(current["outflow"]) == "300.00"
    assert amount_of(current["net"]) == "200.00"
    assert current["savings_rate"] == 40.0
    assert current["transactions_count"] == 5
    assert current["active_days"] == 4
    assert amount_of(current["average_daily_outflow"]) == "42.86"
    assert current["largest_expense"]["name"] == "Rent"
    assert current["largest_expense"]["money"] == {"amount": "108.00", "currency": "EUR"}
    assert current["largest_expense"]["converted"] == {"amount": "120.00", "currency": "USD"}
    assert name_of(current["largest_income"]["category"]) == "Salary"
    assert current["top_expense_category"] == {
        "category": {
            "id": await owner_category_id("Groceries"),
            "name": "Groceries",
            "is_global": False,
        },
        "amount": {"amount": "150.00", "currency": "USD"},
        "share": 50.0,
    }


async def test_overview_summarises_the_previous_window_of_equal_length():
    payload = body_of(await as_user("overview"))
    previous = payload["data"]["previous"]

    assert previous["since"] == "2026-02-22T00:00:00+00:00"
    assert previous["until"] == "2026-03-01T00:00:00+00:00"
    assert amount_of(previous["outflow"]) == "40.00"
    assert previous["savings_rate"] is None


async def test_meta_echoes_the_effective_scope():
    payload = body_of(await as_user("overview", timezone="Europe/Berlin"))

    assert payload["meta"]["since"] == "2026-03-01T00:00:00+00:00"
    assert payload["meta"]["until"] == "2026-03-08T00:00:00+00:00"
    assert payload["meta"]["currency"] == "USD"
    assert payload["meta"]["timezone"] == "Europe/Berlin"
    assert payload["meta"]["wallet_ids"] is None
    assert payload["meta"]["categories"] is None
    assert payload["meta"]["cached"] is False


async def test_a_second_identical_request_is_served_from_the_cache():
    await as_user("overview")
    payload = body_of(await as_user("overview"))

    assert payload["meta"]["cached"] is True
    assert amount_of(payload["data"]["current"]["outflow"]) == "300.00"


async def test_cash_flow_buckets_are_zero_filled_and_carry_closing_balances():
    payload = body_of(await as_user("cash-flow"))
    buckets = payload["data"]["buckets"]

    assert payload["meta"]["granularity"] == "day"
    assert len(buckets) == 7
    assert buckets[0]["start"] == "2026-03-01T00:00:00+00:00"
    assert amount_of(buckets[0]["inflow"]) == "0.00"
    assert buckets[0]["transactions_count"] == 0
    assert amount_of(buckets[0]["closing_balance"]) == "960.00"
    assert amount_of(buckets[5]["outflow"]) == "0.00"
    assert amount_of(buckets[-1]["closing_balance"]) == "1410.00"
    assert payload["data"]["totals"] == {
        "inflow": {"amount": "500.00", "currency": "USD"},
        "outflow": {"amount": "300.00", "currency": "USD"},
        "net": {"amount": "200.00", "currency": "USD"},
    }


async def test_cash_flow_cuts_buckets_at_midnight_in_the_requested_timezone():
    payload = body_of(await as_user("cash-flow", timezone="America/New_York"))
    buckets = payload["data"]["buckets"]

    assert len(buckets) == 8
    assert buckets[0] == {**buckets[0], "start": "2026-03-01T00:00:00+00:00"}
    assert buckets[0]["end"] == "2026-03-01T05:00:00+00:00"
    assert buckets[-1]["end"] == "2026-03-08T00:00:00+00:00"


async def test_cash_flow_and_category_trends_share_their_buckets():
    cash_flow = body_of(await as_user("cash-flow", granularity="week"))
    trends = body_of(await as_user("category-trends", granularity="week"))

    assert [(bucket["start"], bucket["end"]) for bucket in cash_flow["data"]["buckets"]] == [
        (bucket["start"], bucket["end"]) for bucket in trends["data"]["buckets"]
    ]
    assert cash_flow["data"]["buckets"][0]["end"] == "2026-03-02T00:00:00+00:00"


async def test_category_trends_fold_the_tail_into_other():
    payload = body_of(await as_user("category-trends", limit="1"))
    series = payload["data"]["series"]

    assert [entry["key"] for entry in series] == [await owner_category_id("Groceries"), "__other__"]
    assert name_of(series[0]["category"]) == "Groceries"
    assert series[1]["kind"] == "other"
    assert series[1]["category"] is None
    assert amount_of(series[1]["total"]) == "150.00"
    assert all(len(entry["points"]) == 7 for entry in series)


async def test_category_trends_with_a_filter_return_exactly_those_categories():
    rent_id = await owner_category_id("Rent")
    payload = body_of(await as_user("category-trends", category=f"{rent_id},__none__", limit="1"))

    assert [entry["key"] for entry in payload["data"]["series"]] == [rent_id, "__none__"]
    assert [name_of(entry["category"]) for entry in payload["data"]["series"]] == ["Rent", None]
    assert payload["meta"]["categories"] == [rent_id, "__none__"]


async def test_categories_rank_by_amount_and_compare_with_the_previous_window():
    payload = body_of(await as_user("categories"))
    categories = payload["data"]["categories"]

    assert payload["data"]["type"] == "expense"
    assert amount_of(payload["data"]["total"]) == "300.00"
    assert [name_of(category["category"]) for category in categories] == ["Groceries", "Rent", None]
    assert categories[0]["share"] == 50.0
    assert amount_of(categories[0]["average"]) == "75.00"
    assert amount_of(categories[0]["previous_amount"]) == "40.00"
    assert categories[0]["change_percentage"] == 275.0
    assert categories[1]["change_percentage"] is None


async def test_categories_honour_the_uncategorised_token():
    rent_id = await owner_category_id("Rent")
    payload = body_of(await as_user("categories", category=f"{rent_id},__none__"))

    assert [name_of(category["category"]) for category in payload["data"]["categories"]] == [
        "Rent",
        None,
    ]


async def test_an_unknown_category_filter_is_refused():
    response = await as_user("categories", category=str(uuid.uuid4()))

    assert response.status_code == 422
    assert body_of(response)["error"]["details"][0]["code"] == "category_unknown"


async def test_another_users_category_cannot_filter():
    stranger = await get_user_model().objects.aget(username=OTHER_USER_ID)
    their_category = await owned_category(stranger.id, "transaction", "X")

    response = await as_user("categories", category=str(their_category.id))

    assert response.status_code == 422


async def test_money_flow_routes_income_through_wallets_into_expenses():
    payload = body_of(await as_user("money-flow"))
    links = {
        (link["source"], link["target"]): amount_of(link["amount"])
        for link in payload["data"]["links"]
    }
    cash_node = f"wallet:{CASH_WALLET_ID}"
    euro_node = f"wallet:{EURO_WALLET_ID}"
    salary_node = f"income:{await owner_category_id('Salary')}"
    groceries_node = f"expense:{await owner_category_id('Groceries')}"
    rent_node = f"expense:{await owner_category_id('Rent')}"

    assert links == {
        (salary_node, cash_node): "500.00",
        (cash_node, groceries_node): "150.00",
        (cash_node, "expense:__none__"): "30.00",
        (cash_node, "savings"): "320.00",
        (euro_node, rent_node): "120.00",
        ("reserves", euro_node): "120.00",
    }
    assert len(links) == len(payload["data"]["links"])
    nodes = {node["id"]: node for node in payload["data"]["nodes"]}
    assert nodes[cash_node]["wallet"]["name"] == "Cash"
    assert nodes[cash_node]["amount"]["amount"] == "500.00"
    assert nodes["savings"]["label"] == "Saved"
    assert nodes["expense:__none__"]["category"] is None
    assert nodes[groceries_node]["label"] == "Groceries"
    assert name_of(nodes[groceries_node]["category"]) == "Groceries"


async def test_spending_calendar_lists_every_day_and_the_peak():
    payload = body_of(await as_user("spending-calendar"))
    days = payload["data"]["days"]

    assert [day["date"] for day in days] == [f"2026-03-0{day}" for day in range(1, 8)]
    assert amount_of(days[4]["outflow"]) == "80.00"
    assert days[4]["transactions_count"] == 2
    assert amount_of(payload["data"]["peak_outflow"]) == "120.00"


async def test_spending_calendar_refuses_more_than_366_days():
    response = await as_user(
        "spending-calendar",
        since="2025-01-01T00:00:00Z",
        until="2026-03-01T00:00:00Z",
    )

    assert response.status_code == 422
    assert body_of(response)["error"]["details"][0]["code"] == "range_too_long"


async def test_spending_rhythm_has_every_cell_and_names_the_peak():
    payload = body_of(await as_user("spending-rhythm"))
    cells = payload["data"]["cells"]

    assert len(cells) == 168
    assert (cells[0]["weekday"], cells[0]["hour"]) == (1, 0)
    assert (cells[-1]["weekday"], cells[-1]["hour"]) == (7, 23)
    assert payload["data"]["peak"] == {
        "weekday": 3,
        "hour": 10,
        "amount": {"amount": "120.00", "currency": "USD"},
    }


async def test_spending_rhythm_peak_is_null_without_rows():
    payload = body_of(
        await as_user("spending-rhythm", type="income", wallet_id=str(EURO_WALLET_ID))
    )

    assert payload["data"]["peak"] is None


async def test_balance_history_includes_transfers_and_starts_from_the_opening_balance():
    payload = body_of(await as_user("balance-history", points="2"))

    assert payload["data"]["timestamps"] == [
        "2026-03-01T00:00:00+00:00",
        "2026-03-08T00:00:00+00:00",
    ]
    assert [amount_of(total) for total in payload["data"]["total"]] == ["960.00", "1410.00"]
    euro_series = payload["data"]["wallets"][1]
    assert euro_series["wallet"]["currency"] == "EUR"
    assert [amount_of(balance) for balance in euro_series["native_balances"]] == ["0.00", "72.00"]
    assert [amount_of(balance) for balance in euro_series["balances"]] == ["0.00", "80.00"]
    assert payload["meta"]["points"] == 2


async def test_a_wallet_filter_narrows_every_figure():
    overview = body_of(await as_user("overview", wallet_id=str(EURO_WALLET_ID)))
    history = body_of(await as_user("balance-history", wallet_id=str(EURO_WALLET_ID), points="2"))

    assert amount_of(overview["data"]["current"]["outflow"]) == "120.00"
    assert overview["meta"]["wallet_ids"] == [str(EURO_WALLET_ID)]
    assert [series["wallet"]["name"] for series in history["data"]["wallets"]] == ["Euro"]


async def test_counterparties_group_names_case_insensitively():
    payload = body_of(await as_user("counterparties"))
    leader = payload["data"][0]

    assert leader["name"] == "Corner Market"
    assert name_of(leader["category"]) == "Groceries"
    assert amount_of(leader["amount"]) == "150.00"
    assert leader["share"] == 50.0
    assert leader["transactions_count"] == 2
    assert leader["last_seen_at"] == "2026-03-05T18:00:00+00:00"
    assert payload["meta"]["total_counterparties"] == 3


async def test_transactions_drill_down_by_counterparty_with_totals():
    payload = body_of(
        await as_user("transactions", name="  CORNER market", order="created_desc", limit="1")
    )

    assert len(payload["data"]) == 1
    assert payload["data"][0]["created_at"] == "2026-03-05T18:00:00+00:00"
    assert payload["data"][0]["wallet"] == {
        "id": str(CASH_WALLET_ID),
        "name": "Cash",
        "color": "#112233",
    }
    assert payload["meta"]["total"] == 2
    assert amount_of(payload["meta"]["total_outflow"]) == "150.00"
    assert amount_of(payload["meta"]["total_inflow"]) == "0.00"


async def test_transactions_default_to_both_sides_by_amount():
    payload = body_of(await as_user("transactions"))

    assert [transaction["name"] for transaction in payload["data"]][:2] == ["Salary", "Rent"]
    assert payload["meta"]["total"] == 5


@pytest.mark.parametrize(
    ("endpoint", "parameters", "field", "code"),
    [
        ("overview", {"until": "2026-02-01T00:00:00Z"}, "until", "range_invalid"),
        ("overview", {"since": "yesterday"}, "since", "range_invalid"),
        ("overview", {"since": "2019-01-01T00:00:00Z"}, "since", "range_too_long"),
        (
            "cash-flow",
            {"since": "2022-01-01T00:00:00Z", "granularity": "day"},
            "granularity",
            "granularity_too_fine",
        ),
        ("overview", {"wallet_id": str(FOREIGN_WALLET_ID)}, "wallet_id", "wallet_unknown"),
        ("overview", {"wallet_id": str(CLOSED_WALLET_ID)}, "wallet_id", "wallet_unknown"),
        ("overview", {"wallet_id": "not-a-uuid"}, "wallet_id", "wallet_unknown"),
        ("category-trends", {"limit": "8"}, "limit", "limit_out_of_range"),
        ("counterparties", {"limit": "0"}, "limit", "limit_out_of_range"),
        ("transactions", {"limit": "many"}, "limit", "limit_out_of_range"),
        ("balance-history", {"points": "1"}, "points", "points_out_of_range"),
        ("categories", {"type": "transfer"}, "type", "type_invalid"),
        ("transactions", {"order": "name"}, "order", "order_invalid"),
    ],
)
async def test_bad_input_names_the_field_and_the_detail_code(endpoint, parameters, field, code):
    response = await as_user(endpoint, **parameters)
    error = body_of(response)["error"]

    assert response.status_code == 422
    assert error["code"] == "validation_failed"
    assert error["details"] == [
        {"field": field, "code": code, "message": error["details"][0]["message"]}
    ]


async def test_an_unsupported_currency_is_a_top_level_error():
    response = await as_user("overview", currency="XXX")

    assert response.status_code == 422
    assert body_of(response)["error"]["code"] == "unsupported_currency"


async def test_a_read_model_behind_the_requested_version_answers_507():
    response = await AsyncClient().get(
        f"{ANALYTICS}/overview",
        headers={**AUTH_HEADERS, "Read-At-Least": "100"},
    )

    assert response.status_code == 507


async def test_an_opening_balance_moves_the_balance_but_is_never_income():
    overview = body_of(await as_user("overview"))
    income = body_of(await as_user("categories", type="income"))
    payers = body_of(await as_user("counterparties", type="income"))
    flow = body_of(await as_user("money-flow"))
    history = body_of(await as_user("balance-history", wallet_id=str(FRESH_WALLET_ID), points="2"))

    assert amount_of(overview["data"]["current"]["inflow"]) == "500.00"
    assert [name_of(category["category"]) for category in income["data"]["categories"]] == [
        "Salary"
    ]
    assert [payer["name"] for payer in payers["data"]] == ["Salary"]
    assert all(str(FRESH_WALLET_ID) not in node["id"] for node in flow["data"]["nodes"])
    assert [amount_of(total) for total in history["data"]["total"]] == ["0.00", "250.00"]


async def test_a_goal_contribution_leaves_the_wallet_like_a_transfer():
    owner = await get_user_model().objects.aget(username=EXTERNAL_USER_ID)
    contribution_chain = uuid.uuid4()
    await _transaction(
        owner.id,
        CASH_WALLET_ID,
        "-60.00",
        "USD",
        "Trip fund",
        None,
        _at(3, 7, 9),
        chain=contribution_chain,
    )
    await _transaction(
        owner.id,
        GOAL_ID,
        "60.00",
        "USD",
        "Trip fund",
        "Travel",
        _at(3, 7, 9),
        chain=contribution_chain,
        container_kind=MoneyContainers.GOAL,
    )
    await _transaction(
        owner.id,
        GOAL_ID,
        "25.00",
        "USD",
        "Birthday money",
        "Gift",
        _at(3, 7, 10),
        container_kind=MoneyContainers.GOAL,
    )

    overview = body_of(await as_user("overview"))
    history = body_of(await as_user("balance-history", wallet_id=str(CASH_WALLET_ID), points="2"))
    dimensions = body_of(await as_user("dimensions"))

    assert amount_of(overview["data"]["current"]["outflow"]) == "300.00"
    assert amount_of(overview["data"]["current"]["inflow"]) == "500.00"
    assert [amount_of(total) for total in history["data"]["total"]] == ["960.00", "1020.00"]
    assert "Gift" not in dimensions["data"]["categories"]["income"]
