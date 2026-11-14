from dataclasses import dataclass
from datetime import datetime

from data_read_core.shared.analytics import LedgerWallet


@dataclass(frozen=True)
class GetAnalyticsDimensionsQuery:
    user_id: int
    currency: str

    @property
    def cache_signature(self) -> dict:
        return {}


@dataclass(frozen=True)
class DimensionsDTO:
    wallets: list[LedgerWallet]
    expense_categories: list[str]
    income_categories: list[str]
    first_transaction_at: datetime | None
    last_transaction_at: datetime | None
