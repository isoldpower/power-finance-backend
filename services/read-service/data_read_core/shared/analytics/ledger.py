from collections.abc import Iterable
from datetime import datetime
from decimal import Decimal

from data_read_core.shared.exchange_rates import ExchangeRateService

from .config import ZERO, LedgerSide
from .currency_rates import RateTable, build_rate_table
from .ledger_rows import LedgerRow, LedgerRowSelection, LedgerWallet
from .postgres_requests import (
    fetch_ledger_rows,
    fetch_open_wallets,
    sum_native_balances_before,
)
from .scope import AnalyticsScope, AnalyticsWindow


class AnalyticsLedger:
    def __init__(
        self,
        scope: AnalyticsScope,
        open_wallets: list[LedgerWallet],
        rate_service: ExchangeRateService | None = None,
    ) -> None:
        self.scope = scope
        self.open_wallets = open_wallets
        self.selected_wallets = [
            wallet
            for wallet in open_wallets
            if scope.wallet_identifiers is None or wallet.identifier in scope.wallet_identifiers
        ]
        self._wallets_by_identifier = {wallet.identifier: wallet for wallet in open_wallets}
        self._wallet_currencies = {
            wallet.identifier: wallet.currency for wallet in self.selected_wallets
        }
        self._rate_service = rate_service
        self._rate_table = RateTable(target_currency=scope.currency, rates_to_target={})

    @classmethod
    async def load(
        cls,
        scope: AnalyticsScope,
        rate_service: ExchangeRateService | None = None,
    ) -> "AnalyticsLedger":
        ledger = cls(scope, await fetch_open_wallets(scope.user_id), rate_service)
        await ledger._prepare_rates(wallet.currency for wallet in ledger.selected_wallets)

        return ledger

    def wallet(self, wallet_identifier: str) -> LedgerWallet | None:
        return self._wallets_by_identifier.get(wallet_identifier)

    async def fetch_flows(
        self,
        window: AnalyticsWindow,
        *,
        side: LedgerSide | None = None,
        apply_categories: bool = True,
    ) -> list[LedgerRow]:
        return await self._fetch_rows(
            LedgerRowSelection(
                since=window.since,
                until=window.until,
                side=side,
                categories=self.scope.categories if apply_categories else None,
            )
        )

    async def fetch_movements(
        self,
        since: datetime,
        until: datetime,
        *,
        include_until: bool,
    ) -> list[LedgerRow]:
        return await self._fetch_rows(
            LedgerRowSelection(
                since=since,
                until=until,
                include_until=include_until,
                include_balance_movements=True,
            )
        )

    async def native_balances_before(self, instant: datetime) -> dict[str, Decimal]:
        return await sum_native_balances_before(
            self.scope.user_id,
            self._wallet_currencies,
            instant,
        )

    def converted_magnitude(self, row: LedgerRow) -> Decimal:
        return self._rate_table.convert(row.magnitude, row.currency)

    def converted_total(self, rows: Iterable[LedgerRow], side: LedgerSide | None = None) -> Decimal:
        return sum(
            (self.converted_magnitude(row) for row in rows if side is None or row.side is side),
            ZERO,
        )

    def converted_signed(self, row: LedgerRow) -> Decimal:
        return self._rate_table.convert(row.signed_amount, row.currency)

    def converted_balance(self, native_balance: Decimal, wallet: LedgerWallet) -> Decimal:
        return self._rate_table.convert(native_balance, wallet.currency)

    async def _fetch_rows(self, selection: LedgerRowSelection) -> list[LedgerRow]:
        rows = await fetch_ledger_rows(self.scope.user_id, self._wallet_currencies, selection)
        await self._prepare_rates(row.currency for row in rows)

        return rows

    async def _prepare_rates(self, currencies: Iterable[str]) -> None:
        missing_currencies = {
            currency
            for currency in currencies
            if currency
            and currency != self.scope.currency
            and currency not in self._rate_table.rates_to_target
        }
        if not missing_currencies:
            return

        additional_table = await build_rate_table(
            self.scope.currency,
            missing_currencies,
            self._rate_service,
        )
        self._rate_table = RateTable(
            target_currency=self.scope.currency,
            rates_to_target={
                **self._rate_table.rates_to_target,
                **additional_table.rates_to_target,
            },
        )
