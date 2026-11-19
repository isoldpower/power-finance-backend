from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from .config import LedgerSide
from .ledger import AnalyticsLedger
from .ledger_rows import AnalyticsCategory, LedgerRow, LedgerWallet

FALLBACK_WALLET_COLOR = ""


@dataclass(frozen=True)
class TransactionBriefDTO:
    identifier: str
    name: str
    created_at: datetime
    side: LedgerSide
    category: AnalyticsCategory | None
    wallet: LedgerWallet
    native_amount: Decimal
    native_currency: str
    converted_amount: Decimal


def brief_of(row: LedgerRow, ledger: AnalyticsLedger) -> TransactionBriefDTO:
    return TransactionBriefDTO(
        identifier=row.identifier,
        name=row.name,
        created_at=row.created_at,
        side=row.side,
        category=row.category,
        wallet=ledger.wallet(row.wallet_identifier) or _unknown_wallet(row),
        native_amount=row.magnitude,
        native_currency=row.currency,
        converted_amount=ledger.converted_magnitude(row),
    )


def _unknown_wallet(row: LedgerRow) -> LedgerWallet:
    return LedgerWallet(
        identifier=row.wallet_identifier,
        name="",
        color=FALLBACK_WALLET_COLOR,
        currency=row.currency,
        favorite=False,
    )
