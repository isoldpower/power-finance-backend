from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from .wallet_dto import WalletDTO


@dataclass(frozen=True)
class TransactionDTO:
    id: UUID
    amount: Decimal
    currency_code: str
    source_wallet: WalletDTO
    created_at: datetime
    cancels_other: UUID | None = None
    adjusts_other: UUID | None = None


@dataclass(frozen=True)
class TransactionPlainDTO:
    id: UUID
    amount: Decimal
    currency_code: str
    source_wallet_id: str
    created_at: datetime
    cancels_other: UUID | None = None
    adjusts_other: UUID | None = None
