from datetime import datetime
from decimal import Decimal

from .config import ZERO
from .ledger import AnalyticsLedger
from .ledger_rows import LedgerRow


async def native_balance_series(
    ledger: AnalyticsLedger,
    instants: list[datetime],
    *,
    include_instant: bool,
) -> dict[str, list[Decimal]]:
    window = ledger.scope.window
    opening_balances = await ledger.native_balances_before(window.since)
    movements = await ledger.fetch_movements(
        window.since,
        window.until,
        include_until=include_instant,
    )

    return {
        wallet.identifier: _running_balances(
            opening_balances.get(wallet.identifier, ZERO),
            [row for row in movements if row.wallet_identifier == wallet.identifier],
            instants,
            include_instant,
        )
        for wallet in ledger.selected_wallets
    }


def _running_balances(
    opening_balance: Decimal,
    wallet_movements: list[LedgerRow],
    instants: list[datetime],
    include_instant: bool,
) -> list[Decimal]:
    running_balance = opening_balance
    movement_cursor = 0
    balances: list[Decimal] = []

    for instant in instants:
        while movement_cursor < len(wallet_movements) and _is_settled_by(
            wallet_movements[movement_cursor].created_at,
            instant,
            include_instant,
        ):
            running_balance += wallet_movements[movement_cursor].signed_amount
            movement_cursor += 1
        balances.append(running_balance)

    return balances


def _is_settled_by(created_at: datetime, instant: datetime, include_instant: bool) -> bool:
    return created_at <= instant if include_instant else created_at < instant
