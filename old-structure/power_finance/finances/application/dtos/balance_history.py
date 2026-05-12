from dataclasses import dataclass


@dataclass(frozen=True)
class WalletBalanceHistoryItemDTO:
    date: str
    balance: float

@dataclass(frozen=True)
class WalletBalanceHistoryResultDTO:
    history: list[WalletBalanceHistoryItemDTO]
