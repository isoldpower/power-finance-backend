from dataclasses import asdict, dataclass
from decimal import Decimal

from data_read_core.shared.pagination import PageRequest
from data_read_core.shared.postgres_orm import AccountGroups, AccountReadModel
from data_read_core.shared.timestamps import to_iso

ALL_GROUPS = "all"
GROUP_CHOICES = (ALL_GROUPS, *(group.value for group in AccountGroups))


@dataclass(frozen=True)
class ChartFilters:
    """The three query params that narrow the chart, already validated.

    `lowbar` is expressed in `currency`, which is the CALLER's currency and has
    nothing to do with the book currency an account is denominated in — the
    handler converts before it compares."""

    group: str
    lowbar: Decimal
    currency: str

    @property
    def narrows_by_group(self) -> bool:
        return self.group != ALL_GROUPS

    @property
    def narrows_by_balance(self) -> bool:
        """A `lowbar` of zero excludes nothing, so it is not worth a conversion
        or an extra predicate."""

        return self.lowbar > 0

    def as_cache_material(self) -> dict:
        return {
            "group": self.group,
            "lowbar": str(self.lowbar),
            "currency": self.currency,
        }


@dataclass(frozen=True)
class ListAccountsQuery:
    user_id: int
    page: PageRequest
    filters: ChartFilters


@dataclass(frozen=True)
class CacheOperationData:
    user_id: int
    filters: dict
    limit: int
    cursor: str


@dataclass(frozen=True)
class AccountDTO:
    id: str
    user_id: int
    group: str
    name: str
    balance_amount: str
    currency: str
    created_at: str
    updated_at: str | None

    @classmethod
    def from_read_model(cls, model: AccountReadModel) -> "AccountDTO":
        return cls(
            id=str(model.id),
            user_id=model.user_id,
            group=model.group,
            name=model.name,
            balance_amount=str(model.balance),
            currency=model.currency_code,
            created_at=to_iso(model.created_at),
            updated_at=to_iso(model.updated_at),
        )

    @classmethod
    def from_cache(cls, raw: dict) -> "AccountDTO":
        return cls(**raw)

    def to_cache(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class FetchedChart:
    """A page of the chart plus the per-group counts beside it.

    `groups` deliberately ignores the `group` filter — it describes the whole
    chart so the UI can label its tabs — but it DOES honour `lowbar`, so a tab's
    count matches what clicking it returns."""

    rows: list[AccountDTO]
    total: int
    groups: dict[str, int]
    cached: bool
