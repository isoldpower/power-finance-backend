from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from ..contracts import AccountSpec, DispatchedPostings, PostingLeg, TransactionFacts
from ..dispatchers import TemplateAccount, TemplateDispatcher
from ..repositories import AccountRepository

TRANSACTION_ID = UUID("11111111-1111-4111-8111-111111111111")
CONTAINER_ID = UUID("22222222-2222-4222-8222-222222222222")
USER_ID = 7


class StubAccountRepository(AccountRepository):
    """An in-memory chart of accounts that records what was asked of it."""

    def __init__(self, ids: dict[AccountSpec, UUID] | None = None) -> None:
        self._ids = dict(ids or {})
        self.resolved_for: list[int] = []
        self.recomputed: list[set[UUID]] = []

    async def resolve(self, user_id: int, accounts: Sequence[AccountSpec]) -> list[UUID]:
        self.resolved_for.append(user_id)
        return [self._ids[spec] for spec in accounts]

    async def recompute_balances(self, account_ids, now: datetime) -> list:
        self.recomputed.append(set(account_ids))
        return []


def build_transaction_facts(
    *,
    amount: Decimal = Decimal("125.00"),
    name: str = "Groceries",
    currency_code: str = "EUR",
) -> TransactionFacts:
    """The facts a dispatcher is handed, without a database to read them from."""

    return TransactionFacts(
        id=TRANSACTION_ID,
        user_id=USER_ID,
        container_id=CONTAINER_ID,
        container_kind="wallet",
        amount=amount,
        created_at=datetime(2026, 8, 25, 12, 0, tzinfo=UTC),
        currency_code=currency_code,
        name=name,
        category="food",
        origin="manual",
    )


class SingleLegDispatcher:
    """A dispatcher that answers with one leg against a given account, so a test
    can tell whose answer reached the database."""

    def __init__(self, account_id: UUID, amount: Decimal = Decimal("1.00")) -> None:
        self._account_id = account_id
        self._amount = amount
        self.calls: list[UUID] = []

    async def dispatch(self, transaction: TransactionFacts) -> DispatchedPostings:
        self.calls.append(transaction.id)
        return DispatchedPostings(
            legs=(
                PostingLeg(
                    account_id=self._account_id,
                    title="spike",
                    debit=True,
                    amount=self._amount,
                    position=0,
                ),
            ),
            balanced=False,
            comment="single leg",
            backend="fake",
        )


# This slice's own copy of the chart. `background_workers` holds the one the
# service runs on and has a test that the two agree.
TEMPLATE_ACCOUNTS: tuple[TemplateAccount, ...] = (
    TemplateAccount(AccountSpec(group="liabilities", name="temporary-liability"), debit=True),
    TemplateAccount(AccountSpec(group="assets", name="temporary-assets"), debit=False),
)


def build_template_dispatcher(accounts) -> TemplateDispatcher:
    return TemplateDispatcher(accounts, TEMPLATE_ACCOUNTS)


class FixedRates:
    """An `ExchangeRates` that quotes what the test says.

    Booking multiplies by a rate, so without this the arithmetic under test
    would be whatever the live feed happened to say today — and the suite would
    need the internet to pass. Same-currency short-circuits to 1, as the real
    service does, so a test only has to name the rate it cares about.
    """

    def __init__(self, rate: Decimal = Decimal(1)) -> None:
        self.rate = rate
        self.asked: list[tuple[str, str]] = []

    async def rate_between(self, base_code: str, quote_code: str) -> tuple[Decimal, object]:
        self.asked.append((base_code, quote_code))
        if base_code.upper() == quote_code.upper():
            return Decimal(1), None

        return self.rate, None
