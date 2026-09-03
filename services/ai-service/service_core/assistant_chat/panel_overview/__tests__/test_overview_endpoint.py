"""`GET /assistant/overview` — the cached, pollable half of the panel."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from service_core.shared.db_connection import (
    ProjectedTransaction,
    UserModel,
    get_session_factory,
    session_scope,
)
from service_core.shared.http_contract import ApiError, error_response

from .. import OverviewCache, OverviewService, SqlAlchemyActivitySource
from ..contracts import ActivitySource, ConversationActivity
from ..http import build_overview_router

AUTHENTICATED = {"X-User-Id": "clerk_7"}
OVERVIEW = "/api/v1/assistant/overview"
NOW = datetime.now(UTC)
THIS_MONTH = NOW.replace(day=1, hour=12, minute=0, second=0, microsecond=0)


class CountingActivitySource(ActivitySource):
    def __init__(self) -> None:
        self.reads = 0

    async def read(self, external_id: str) -> ConversationActivity:
        self.reads += 1

        return ConversationActivity(
            spend_currency="USD",
            spend_this_month=Decimal(0),
            spend_last_month=Decimal(0),
            uncategorised=0,
            recorded_this_month=0,
        )


def _client(service: OverviewService) -> TestClient:
    app = FastAPI()

    @app.exception_handler(ApiError)
    async def handle(request: Request, failure: ApiError) -> JSONResponse:
        return error_response(request, failure)

    app.include_router(build_overview_router(service), prefix="/api/v1")

    return TestClient(app)


def _live_service() -> OverviewService:
    return OverviewService(
        activity=SqlAlchemyActivitySource(get_session_factory()),
        cache=OverviewCache(),
    )


async def _user(external_id: str = "clerk_7", user_id: int = 1) -> int:
    async with session_scope() as session:
        session.add(UserModel(user_id=user_id, external_id=external_id, created_at=NOW))

    return user_id


async def _transaction(user_id: int, amount: str, category: str = "Dining") -> None:
    async with session_scope() as session:
        session.add(
            ProjectedTransaction(
                id=uuid4(),
                user_id=user_id,
                container_id=uuid4(),
                container_kind="wallet",
                amount=Decimal(amount),
                currency_code="USD",
                category=category,
                created_at=THIS_MONTH,
            )
        )


async def test_the_panel_is_signals_and_prompts():
    await _user()

    body = _client(_live_service()).get(OVERVIEW, headers=AUTHENTICATED).json()

    assert set(body["data"]) == {"signals", "prompts"}
    assert all(set(signal) == {"label", "value", "tone"} for signal in body["data"]["signals"])


async def test_signal_values_are_strings_not_numbers():
    """The one deliberate formatting exception in the API. A client renders
    them verbatim and must never parse one back into a number."""

    await _user()

    signals = (
        _client(_live_service()).get(OVERVIEW, headers=AUTHENTICATED).json()["data"]["signals"]
    )

    assert all(isinstance(signal["value"], str) for signal in signals)


async def test_uncategorised_transactions_are_counted():
    user_id = await _user()
    await _transaction(user_id, "-10.00", category="")
    await _transaction(user_id, "-20.00", category="")
    await _transaction(user_id, "-30.00", category="Dining")

    signals = (
        _client(_live_service()).get(OVERVIEW, headers=AUTHENTICATED).json()["data"]["signals"]
    )
    uncategorised = next(signal for signal in signals if signal["label"] == "Uncategorised")

    assert uncategorised["value"] == "2 transactions"


async def test_a_user_with_no_ledger_still_gets_a_panel():
    """The conversation can start before `UserSynced` has arrived."""

    response = _client(_live_service()).get(OVERVIEW, headers=AUTHENTICATED)

    assert response.status_code == 200
    assert response.json()["data"]["prompts"]


async def test_the_read_is_cached_and_says_so():
    activity = CountingActivitySource()
    client = _client(OverviewService(activity=activity, cache=OverviewCache()))

    first = client.get(OVERVIEW, headers=AUTHENTICATED).json()
    second = client.get(OVERVIEW, headers=AUTHENTICATED).json()

    assert first["meta"]["cached"] is False
    assert second["meta"]["cached"] is True
    assert activity.reads == 1


async def test_the_cache_is_per_user():
    activity = CountingActivitySource()
    client = _client(OverviewService(activity=activity, cache=OverviewCache()))

    client.get(OVERVIEW, headers=AUTHENTICATED)
    other = client.get(OVERVIEW, headers={"X-User-Id": "clerk_9"}).json()

    assert other["meta"]["cached"] is False
    assert activity.reads == 2


async def test_an_expired_entry_is_recomputed():
    activity = CountingActivitySource()
    client = _client(OverviewService(activity=activity, cache=OverviewCache(ttl_seconds=0)))

    client.get(OVERVIEW, headers=AUTHENTICATED)
    second = client.get(OVERVIEW, headers=AUTHENTICATED).json()

    assert second["meta"]["cached"] is False
    assert activity.reads == 2


async def test_a_request_that_did_not_pass_the_gateway_is_refused():
    response = _client(_live_service()).get(OVERVIEW)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"
