from dataclasses import asdict, dataclass
from decimal import Decimal
from zoneinfo import ZoneInfo

from data_read_core.shared.pagination import PageRequest
from data_read_core.shared.postgres_orm import TransactionReadModel, WalletReadModel
from data_read_core.shared.timestamps import DEFAULT_PERIOD, Period, to_iso


@dataclass(frozen=True)
class GetWalletQuery:
    user_id: int
    wallet_id: str
    zone: ZoneInfo
    recent_page: PageRequest
    period: Period = DEFAULT_PERIOD


@dataclass(frozen=True)
class PeriodFlowsAnalysis:
    """Money that moved through the wallet over the requested window, in the
    WALLET's currency. Nothing is converted — this is wallet detail, not
    Metrics."""

    inflow: Decimal
    outflow: Decimal


@dataclass(frozen=True)
class WalletDTO:
    id: str
    user_id: int
    name: str
    balance_amount: str
    zero_balance_amount: str
    currency: str
    created_at: str
    updated_at: str | None
    deleted_at: str | None
    category: str
    color: str
    favorite: bool

    @classmethod
    def from_read_model(cls, model: WalletReadModel) -> "WalletDTO":
        return cls(
            id=str(model.id),
            user_id=model.user_id,
            name=model.title,
            balance_amount=str(model.balance),
            zero_balance_amount=str(model.zero_balance),
            currency=model.currency_code,
            created_at=to_iso(model.created_at),
            updated_at=to_iso(model.updated_at),
            deleted_at=to_iso(model.deleted_at),
            category=model.category,
            color=model.color,
            favorite=model.favorite,
        )

    @classmethod
    def from_cache(cls, raw: dict) -> "WalletDTO":
        return cls(**raw)

    def to_cache(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class RecentTransactionDTO:
    id: str
    wallet_id: str
    wallet_name: str
    name: str
    amount: str
    currency: str
    category: str | None
    origin: str
    chain_id: str | None
    chain_sort: str
    created_at: str
    updated_at: str | None
    deleted_at: str | None

    @classmethod
    def from_read_model(cls, model: TransactionReadModel) -> "RecentTransactionDTO":
        return cls(
            id=str(model.id),
            wallet_id=str(model.wallet_id),
            wallet_name=model.wallet_name,
            name=model.name,
            amount=str(model.amount),
            currency=model.currency_code,
            category=model.category,
            origin=model.origin,
            chain_id=str(model.chain_id) if model.chain_id else None,
            chain_sort=str(model.chain_sort),
            created_at=to_iso(model.created_at),
            updated_at=to_iso(model.updated_at),
            deleted_at=to_iso(model.deleted_at),
        )


@dataclass(frozen=True)
class WalletDetailDTO:
    wallet: WalletDTO
    period: PeriodFlowsAnalysis
    recent: list[RecentTransactionDTO]
    recent_total: int
