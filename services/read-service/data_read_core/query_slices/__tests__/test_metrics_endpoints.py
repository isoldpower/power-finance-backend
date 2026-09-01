"""The three derived views over accounts and transactions, on one endpoint.

Every figure here is reported in the caller's PREFERRED currency, which arrives
as a gateway header. The tests lean on that rather than on a query param
because there deliberately is no query param — a per-request override would be
a second way to choose the reporting currency.

The sections live behind boolean selectors on a single `GET /metrics` rather
than behind three paths: they read the same rows and differ only in the fold.
"""

import json
import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.test import AsyncClient

from data_read_core.query_slices.get_metrics import query_handler
from data_read_core.shared.exchange_rates import get_rate_service
from data_read_core.shared.money import CURRENCY_CATALOG
from data_read_core.shared.postgres_orm import (
    NO_CHAIN_SENTINEL,
    AccountDispatchReadModel,
    AccountReadModel,
    CurrencyReadModel,
    TransactionReadModel,
)
from data_read_core.shared.redis_cache import get_redis

pytestmark = pytest.mark.django_db(transaction=True)

EXTERNAL_USER_ID = "user_metrics"
OTHER_USER_ID = "user_other_metrics"
AUTH_HEADERS = {"X-User-Id": EXTERNAL_USER_ID}
WALLET_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
METRICS = "/api/v1/metrics"

JANUARY = datetime(2026, 1, 10, tzinfo=UTC)
FEBRUARY = datetime(2026, 2, 10, tzinfo=UTC)
MARCH = datetime(2026, 3, 10, tzinfo=UTC)

CACHE_PREFIXES = (
    "read:metrics:*",
    "ver:accounts:*",
    "ver:transactions:*",
    "read:rates:*",
)


def as_user(path: str, **headers):
    return AsyncClient().get(path, headers={**AUTH_HEADERS, **headers})


def body_of(response) -> dict:
    return json.loads(response.content)


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
async def _provisioned():
    CURRENCY_CATALOG.reset()
    await get_user_model().objects.acreate(username=EXTERNAL_USER_ID)
    await get_user_model().objects.acreate(username=OTHER_USER_ID)
    await CurrencyReadModel.objects.abulk_create(
        [
            CurrencyReadModel(code="USD", name="US Dollar", symbol="$", numeric="840", digits=2),
            CurrencyReadModel(code="JPY", name="Yen", symbol="¥", numeric="392", digits=0),
            CurrencyReadModel(code="EUR", name="Euro", symbol="€", numeric="978", digits=2),
        ],
        ignore_conflicts=True,
    )
    yield
    CURRENCY_CATALOG.reset()


async def _user_id(username: str = EXTERNAL_USER_ID) -> int:
    user = await get_user_model().objects.aget(username=username)
    return user.id


async def _account(
    *,
    group: str,
    name: str,
    balance: str,
    currency: str = "USD",
    owner: str = EXTERNAL_USER_ID,
) -> AccountReadModel:
    return await AccountReadModel.objects.acreate(
        id=uuid.uuid4(),
        user_id=await _user_id(owner),
        group=group,
        name=name,
        balance=Decimal(balance),
        currency_code=currency,
        created_at=JANUARY,
    )


async def _transaction(
    *,
    amount: str,
    created_at: datetime = FEBRUARY,
    currency: str = "USD",
    chain_id: uuid.UUID | None = None,
    deleted_at: datetime | None = None,
    owner: str = EXTERNAL_USER_ID,
) -> TransactionReadModel:
    return await TransactionReadModel.objects.acreate(
        id=uuid.uuid4(),
        wallet_id=WALLET_ID,
        wallet_name="Main",
        user_id=await _user_id(owner),
        amount=Decimal(amount),
        currency_code=currency,
        name="Something",
        chain_id=chain_id,
        chain_sort=chain_id or NO_CHAIN_SENTINEL,
        occurred_at=created_at,
        created_at=created_at,
        deleted_at=deleted_at,
    )


# --- the balance section ----------------------------------------------------


async def test_the_sheet_folds_the_chart_into_three_groups():
    await _account(group="assets", name="cash", balance="100.00")
    await _account(group="assets", name="savings", balance="50.00")
    await _account(group="liabilities", name="card", balance="20.00")
    await _account(group="equity", name="retained", balance="130.00")

    payload = body_of(await as_user(METRICS))

    assert payload["data"]["balance"]["assets"] == {"amount": "150.00", "currency": "USD"}
    assert payload["data"]["balance"]["liabilities"] == {"amount": "20.00", "currency": "USD"}
    assert payload["data"]["balance"]["equity"] == {"amount": "130.00", "currency": "USD"}


async def test_a_sheet_that_satisfies_the_identity_balances_with_no_comment():
    """Amounts are normal-balance positive, so the identity to check is
    `assets == liabilities + equity`, not a sum against zero."""

    await _account(group="assets", name="cash", balance="150.00")
    await _account(group="liabilities", name="card", balance="20.00")
    await _account(group="equity", name="retained", balance="130.00")

    payload = body_of(await as_user(METRICS))

    assert payload["data"]["balance"]["balanced"] is True
    assert payload["data"]["balance"]["comments"] is None


async def test_a_drifting_sheet_reports_the_gap_rather_than_failing():
    await _account(group="assets", name="cash", balance="150.00")
    await _account(group="liabilities", name="card", balance="20.00")

    response = await as_user(METRICS)
    payload = body_of(response)

    assert response.status_code == 200
    assert payload["data"]["balance"]["balanced"] is False
    assert "130" in payload["data"]["balance"]["comments"]


async def test_a_dispatch_whose_legs_disagreed_unbalances_the_sheet():
    """The totals can satisfy the identity and still be built on a posting that
    did not, so the two are asked about separately."""

    await _account(group="assets", name="cash", balance="150.00")
    await _account(group="liabilities", name="card", balance="20.00")
    await _account(group="equity", name="retained", balance="130.00")
    await AccountDispatchReadModel.objects.acreate(
        transaction_id=uuid.uuid4(),
        user_id=await _user_id(),
        dispatch_id=uuid.uuid4(),
        balanced=False,
        comment="legs disagree",
        backend="template",
        created_count=2,
        deleted_count=0,
        dispatched_at=FEBRUARY,
    )

    payload = body_of(await as_user(METRICS))

    assert payload["data"]["balance"]["balanced"] is False
    assert "did not agree" in payload["data"]["balance"]["comments"]


async def test_the_sheet_converts_into_the_preferred_currency():
    """The static rate table puts JPY at 150 to the dollar."""

    await _account(group="assets", name="cash", balance="100.00", currency="USD")

    payload = body_of(await as_user(METRICS, **{"X-User-Currency": "JPY"}))

    assert payload["data"]["balance"]["assets"] == {"amount": "15000", "currency": "JPY"}


async def test_the_sheet_ignores_someone_else_s_accounts():
    await _account(group="assets", name="mine", balance="10.00")
    await _account(group="assets", name="theirs", balance="999.00", owner=OTHER_USER_ID)

    payload = body_of(await as_user(METRICS))

    assert payload["data"]["balance"]["assets"]["amount"] == "10.00"


async def test_the_sheet_reports_whether_it_was_cached():
    await _account(group="assets", name="cash", balance="10.00")

    first = body_of(await as_user(METRICS))
    second = body_of(await as_user(METRICS))

    assert first["meta"]["cached"] is False
    assert second["meta"]["cached"] is True


async def test_two_preferred_currencies_do_not_share_a_cache_entry():
    """A preference is not a write, so nothing evicts when one changes. The
    currency has to be part of the key or the second caller reads the first
    caller's denomination."""

    await _account(group="assets", name="cash", balance="100.00")

    await as_user(METRICS)
    payload = body_of(await as_user(METRICS, **{"X-User-Currency": "JPY"}))

    assert payload["data"]["balance"]["assets"] == {"amount": "15000", "currency": "JPY"}


# --- the net_worth section --------------------------------------------------


async def test_net_worth_is_the_running_total_of_every_transaction():
    await _transaction(amount="100.00", created_at=JANUARY)
    await _transaction(amount="-30.00", created_at=FEBRUARY)

    payload = body_of(await as_user(METRICS))

    assert payload["data"]["net_worth"]["money"] == {"amount": "70.00", "currency": "USD"}


async def test_a_cancelled_transaction_never_counted_as_held():
    await _transaction(amount="100.00", created_at=JANUARY)
    await _transaction(amount="999.00", created_at=FEBRUARY, deleted_at=MARCH)

    payload = body_of(await as_user(METRICS))

    assert payload["data"]["net_worth"]["money"]["amount"] == "100.00"


async def test_a_transfer_leaves_net_worth_untouched():
    """Both legs of a chain belong to the same user, so they cancel without
    anything having to know a chain is a transfer."""

    chain = uuid.uuid4()
    await _transaction(amount="100.00", created_at=JANUARY)
    await _transaction(amount="-40.00", created_at=FEBRUARY, chain_id=chain)
    await _transaction(amount="40.00", created_at=FEBRUARY, chain_id=chain)

    payload = body_of(await as_user(METRICS))

    assert payload["data"]["net_worth"]["money"]["amount"] == "100.00"


async def test_the_series_is_exactly_points_long_and_is_not_paginated():
    await _transaction(amount="100.00", created_at=JANUARY)

    payload = body_of(await as_user(f"{METRICS}?points=4"))

    assert len(payload["data"]["net_worth"]["series"]) == 4
    assert payload["meta"]["points"] == 4
    assert "next_cursor" not in payload["meta"]


async def test_the_series_ends_where_the_reported_total_does():
    """Each point is the running total at the END of its slice, so the curve
    reads as net worth over time rather than as activity per slice."""

    await _transaction(amount="100.00", created_at=JANUARY)
    await _transaction(amount="-30.00", created_at=FEBRUARY)

    payload = body_of(await as_user(f"{METRICS}?points=5"))

    assert (
        payload["data"]["net_worth"]["series"][-1]["money"] == payload["data"]["net_worth"]["money"]
    )


async def test_points_is_clamped_rather_than_rejected():
    await _transaction(amount="10.00")

    payload = body_of(await as_user(f"{METRICS}?points=9999"))

    assert payload["meta"]["points"] == 100
    assert len(payload["data"]["net_worth"]["series"]) == 100


async def test_a_non_integer_points_blames_points_and_not_limit():
    response = await as_user(f"{METRICS}?points=many")
    payload = body_of(response)

    assert response.status_code == 422
    assert payload["error"]["details"][0]["field"] == "points"


async def test_a_malformed_since_is_rejected():
    response = await as_user(f"{METRICS}?since=yesterday")
    payload = body_of(response)

    assert response.status_code == 422
    assert payload["error"]["details"][0]["field"] == "since"


async def test_since_is_echoed_and_null_means_all_time():
    await _transaction(amount="10.00")

    all_time = body_of(await as_user(METRICS))
    bounded = body_of(await as_user(f"{METRICS}?since=2026-02-01T00:00:00Z"))

    assert all_time["meta"]["since"] is None
    assert bounded["meta"]["since"] == "2026-02-01T00:00:00+00:00"


async def test_the_window_opens_on_what_was_already_held():
    """`since` selects the window, not the balance. Money held before it still
    counts toward net worth — otherwise the curve would describe the window's
    activity rather than the user's worth."""

    await _transaction(amount="100.00", created_at=JANUARY)
    await _transaction(amount="20.00", created_at=MARCH)

    payload = body_of(await as_user(f"{METRICS}?since=2026-03-01T00:00:00Z"))

    assert payload["data"]["net_worth"]["money"]["amount"] == "120.00"
    assert payload["data"]["net_worth"]["net_diff"]["direction"] == "up"


async def test_a_window_in_which_nothing_moved_is_flat():
    """`flat` is a real direction, not the absence of one."""

    await _transaction(amount="100.00", created_at=JANUARY)

    payload = body_of(await as_user(f"{METRICS}?since=2026-03-01T00:00:00Z"))

    assert payload["data"]["net_worth"]["net_diff"]["direction"] == "flat"
    assert payload["data"]["net_worth"]["net_diff"]["percentage"] == 0


async def test_losing_money_over_the_window_reads_as_down():
    await _transaction(amount="100.00", created_at=JANUARY)
    await _transaction(amount="-25.00", created_at=MARCH)

    payload = body_of(await as_user(f"{METRICS}?since=2026-03-01T00:00:00Z"))

    assert payload["data"]["net_worth"]["net_diff"]["direction"] == "down"
    assert payload["data"]["net_worth"]["net_diff"]["percentage"] == -25.0


async def test_growth_from_nothing_reports_no_percentage():
    """Every gain from zero is infinite growth. `direction` still says which
    way it went, so the client is not left guessing."""

    await _transaction(amount="100.00", created_at=MARCH)

    payload = body_of(await as_user(f"{METRICS}?since=2026-03-01T00:00:00Z"))

    assert payload["data"]["net_worth"]["net_diff"]["percentage"] is None
    assert payload["data"]["net_worth"]["net_diff"]["direction"] == "up"


async def test_net_worth_folds_currencies_before_it_totals():
    await _transaction(amount="100.00", created_at=JANUARY, currency="USD")
    await _transaction(amount="150.00", created_at=FEBRUARY, currency="JPY")

    payload = body_of(await as_user(METRICS))

    assert payload["data"]["net_worth"]["money"] == {"amount": "101.00", "currency": "USD"}


# --- the cash_flow section --------------------------------------------------


async def test_cash_flow_reports_both_directions_as_positive_magnitudes():
    await _transaction(amount="150.00", created_at=JANUARY)
    await _transaction(amount="-100.00", created_at=FEBRUARY)

    payload = body_of(await as_user(METRICS))

    assert payload["data"]["cash_flow"]["inflow"] == {"amount": "150.00", "currency": "USD"}
    assert payload["data"]["cash_flow"]["outflow"] == {"amount": "100.00", "currency": "USD"}
    assert payload["data"]["cash_flow"]["total_net"] == {"amount": "50.00", "currency": "USD"}


async def test_the_savings_rate_is_a_bare_number_not_money():
    await _transaction(amount="200.00", created_at=JANUARY)
    await _transaction(amount="-50.00", created_at=FEBRUARY)

    payload = body_of(await as_user(METRICS))

    assert payload["data"]["cash_flow"]["savings_rate"] == 75.0


async def test_a_period_with_no_income_reports_no_savings_rate():
    """A rate against no income is undefined. Zero would claim the user saved
    nothing, when in fact there was nothing to save."""

    await _transaction(amount="-50.00", created_at=FEBRUARY)

    payload = body_of(await as_user(METRICS))

    assert payload["data"]["cash_flow"]["savings_rate"] is None
    assert payload["data"]["cash_flow"]["total_net"] == {"amount": "-50.00", "currency": "USD"}


async def test_transfers_are_excluded_from_both_halves():
    """A chain moves money between two containers the user already owns.
    Counting it would report the same money as income and as spending, which
    nets out of `total_net` but inflates the two figures above it — and makes
    `savings_rate` describe nothing."""

    chain = uuid.uuid4()
    await _transaction(amount="100.00", created_at=JANUARY)
    await _transaction(amount="-40.00", created_at=FEBRUARY, chain_id=chain)
    await _transaction(amount="40.00", created_at=FEBRUARY, chain_id=chain)

    payload = body_of(await as_user(METRICS))

    assert payload["data"]["cash_flow"]["inflow"]["amount"] == "100.00"
    assert payload["data"]["cash_flow"]["outflow"]["amount"] == "0.00"
    assert payload["data"]["cash_flow"]["savings_rate"] == 100.0


async def test_since_narrows_the_period():
    await _transaction(amount="500.00", created_at=JANUARY)
    await _transaction(amount="100.00", created_at=MARCH)

    payload = body_of(await as_user(f"{METRICS}?since=2026-03-01T00:00:00Z"))

    assert payload["data"]["cash_flow"]["inflow"]["amount"] == "100.00"
    assert payload["meta"]["since"] == "2026-03-01T00:00:00+00:00"


async def test_a_cancelled_transaction_is_not_a_flow():
    await _transaction(amount="100.00", created_at=JANUARY)
    await _transaction(amount="999.00", created_at=FEBRUARY, deleted_at=MARCH)

    payload = body_of(await as_user(METRICS))

    assert payload["data"]["cash_flow"]["inflow"]["amount"] == "100.00"


async def test_cash_flow_converts_into_the_preferred_currency():
    await _transaction(amount="150.00", created_at=JANUARY, currency="JPY")

    payload = body_of(await as_user(METRICS))

    assert payload["data"]["cash_flow"]["inflow"] == {"amount": "1.00", "currency": "USD"}


async def test_cash_flow_ignores_someone_else_s_money():
    await _transaction(amount="10.00")
    await _transaction(amount="999.00", owner=OTHER_USER_ID)

    payload = body_of(await as_user(METRICS))

    assert payload["data"]["cash_flow"]["inflow"]["amount"] == "10.00"


async def test_cash_flow_reports_whether_it_was_cached():
    await _transaction(amount="10.00")

    first = body_of(await as_user(METRICS))
    second = body_of(await as_user(METRICS))

    assert first["meta"]["cached"] is False
    assert second["meta"]["cached"] is True


async def test_a_new_transaction_invalidates_every_cached_metric():
    """Metrics are keyed on the transaction AND account version counters the
    write reactions already bump, so neither needs a counter of its own."""

    await _transaction(amount="10.00")
    assert body_of(await as_user(METRICS))["data"]["cash_flow"]["inflow"]["amount"] == "10.00"

    await get_redis().incr(f"ver:transactions:{await _user_id()}")
    await _transaction(amount="5.00")

    payload = body_of(await as_user(METRICS))

    assert payload["data"]["cash_flow"]["inflow"]["amount"] == "15.00"
    assert payload["meta"]["cached"] is False


# --- edges ------------------------------------------------------------------


async def test_a_user_with_nothing_gets_zeroes_rather_than_an_error():
    """With no transactions there is no first one to open the window on, so
    `since` and `until` collapse onto the same instant. The series still has to
    come back the documented length rather than divide by a zero-width slice."""

    net_worth = body_of(await as_user(f"{METRICS}?points=3"))
    cash_flow = body_of(await as_user(METRICS))
    balance = body_of(await as_user(METRICS))

    assert net_worth["data"]["net_worth"]["money"] == {"amount": "0.00", "currency": "USD"}
    assert [point["money"]["amount"] for point in net_worth["data"]["net_worth"]["series"]] == [
        "0.00"
    ] * 3
    assert net_worth["data"]["net_worth"]["net_diff"]["direction"] == "flat"
    assert cash_flow["data"]["cash_flow"]["total_net"]["amount"] == "0.00"
    assert balance["data"]["balance"]["balanced"] is True


async def test_a_zero_scale_currency_is_never_padded_with_a_minor_unit():
    """JPY has no minor unit, so rendering the fold at two decimals would
    invent one."""

    await _transaction(amount="100.00", created_at=JANUARY, currency="USD")

    payload = body_of(await as_user(METRICS, **{"X-User-Currency": "JPY"}))

    assert payload["data"]["net_worth"]["money"] == {"amount": "15000", "currency": "JPY"}
    assert payload["data"]["net_worth"]["series"][-1]["money"]["amount"] == "15000"


# --- section selection ------------------------------------------------------


async def test_a_bare_request_returns_every_section():
    """The reason this is one endpoint: the dashboard call asks for nothing and
    gets all three."""

    await _transaction(amount="10.00")

    payload = body_of(await as_user(METRICS))

    assert payload["data"]["balance"] is not None
    assert payload["data"]["net_worth"] is not None
    assert payload["data"]["cash_flow"] is not None
    assert payload["meta"]["sections"] == ["balance", "net-worth", "cash-flow"]


async def test_an_excluded_section_is_null_rather_than_missing():
    """A client reads the same three keys on every response instead of
    branching on whether one exists."""

    await _transaction(amount="10.00")

    payload = body_of(await as_user(f"{METRICS}?cash-flow=false"))

    assert payload["data"]["cash_flow"] is None
    assert payload["data"]["net_worth"] is not None
    assert payload["meta"]["sections"] == ["balance", "net-worth"]


async def test_sections_can_be_dropped_independently():
    await _transaction(amount="10.00")

    payload = body_of(await as_user(f"{METRICS}?balance=false&net-worth=false"))

    assert payload["data"]["balance"] is None
    assert payload["data"]["net_worth"] is None
    assert payload["data"]["cash_flow"] is not None
    assert payload["meta"]["sections"] == ["cash-flow"]


async def test_asking_for_nothing_is_a_well_formed_empty_response():
    """Not an error: it is a valid request for no sections, and the envelope
    has a shape for it."""

    response = await as_user(f"{METRICS}?balance=false&net-worth=false&cash-flow=false")
    payload = body_of(response)

    assert response.status_code == 200
    assert payload["data"] == {"balance": None, "net_worth": None, "cash_flow": None}
    assert payload["meta"]["sections"] == []


async def test_a_selector_accepts_the_usual_boolean_spellings():
    await _transaction(amount="10.00")

    for spelling in ("false", "FALSE", "0", "no", "off"):
        payload = body_of(await as_user(f"{METRICS}?balance={spelling}"))
        assert payload["data"]["balance"] is None, spelling

    for spelling in ("true", "1", "yes", "on"):
        payload = body_of(await as_user(f"{METRICS}?balance={spelling}"))
        assert payload["data"]["balance"] is not None, spelling


async def test_a_selector_that_is_not_a_boolean_names_itself():
    response = await as_user(f"{METRICS}?net-worth=maybe")
    payload = body_of(response)

    assert response.status_code == 422
    assert payload["error"]["details"][0]["field"] == "net-worth"


async def test_two_section_sets_do_not_share_a_cache_entry():
    """Sections decide what the payload contains, so they belong in the key
    exactly as `since` and `points` do."""

    await _transaction(amount="10.00")

    await as_user(f"{METRICS}?cash-flow=false")
    payload = body_of(await as_user(METRICS))

    assert payload["data"]["cash_flow"] is not None
    assert payload["meta"]["cached"] is False


async def test_a_dropped_section_costs_none_of_its_queries(monkeypatch):
    """The saving is the point of the merge, so it is asserted rather than
    assumed: asking for cash flow alone must not read the chart of accounts,
    and must not bucket a series nobody will look at."""

    await _transaction(amount="10.00")
    await _account(group="assets", name="cash", balance="10.00")

    for name in (
        "sum_accounts_by_group_and_currency",
        "count_unbalanced_dispatches",
        "sum_by_bucket",
    ):
        monkeypatch.setattr(query_handler, name, _refuses(name))

    payload = body_of(await as_user(f"{METRICS}?balance=false&net-worth=false"))

    assert payload["data"]["cash_flow"]["inflow"]["amount"] == "10.00"


async def test_the_sections_share_one_pass_over_the_transactions(monkeypatch):
    """Net worth's opening balance, its all-time total and cash flow's two
    directional figures are conditional aggregates in ONE query — which is what
    a single endpoint buys over three."""

    await _transaction(amount="10.00")

    calls: list[str] = []
    original = query_handler.aggregate_transactions

    async def counting(*args, **kwargs):
        calls.append("aggregate")
        return await original(*args, **kwargs)

    monkeypatch.setattr(query_handler, "aggregate_transactions", counting)

    await as_user(METRICS)

    assert calls == ["aggregate"]


def _refuses(name: str):
    async def refused(*args, **kwargs):
        raise AssertionError(f"{name} should not have been called")

    return refused
