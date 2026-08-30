from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from ..contracts import AccountSpec, TransactionFacts
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
) -> TransactionFacts:
    """The facts a dispatcher is handed, without a database to read them from."""

    return TransactionFacts(
        id=TRANSACTION_ID,
        user_id=USER_ID,
        container_id=CONTAINER_ID,
        container_kind="wallet",
        amount=amount,
        created_at=datetime(2026, 8, 25, 12, 0, tzinfo=UTC),
        name=name,
        category="food",
        origin="manual",
    )


# This slice's own copy of the chart. `background_workers` holds the one the
# service runs on and has a test that the two agree.
TEMPLATE_ACCOUNTS: tuple[TemplateAccount, ...] = (
    TemplateAccount(AccountSpec(group="liabilities", name="temporary-liability"), debit=True),
    TemplateAccount(AccountSpec(group="assets", name="temporary-assets"), debit=False),
)


def build_template_dispatcher(accounts) -> TemplateDispatcher:
    return TemplateDispatcher(accounts, TEMPLATE_ACCOUNTS)
