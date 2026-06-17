from dataclasses import dataclass
from decimal import Decimal

from ..exceptions import CurrencyMismatchError, NegativeMoneyError


@dataclass(frozen=True)
class Money:
    """Money dataclass used to bind amount to currency."""

    amount: Decimal
    currency_code: str

    def __str__(self) -> str:
        return f"{self.amount} {self.currency_code}"

    def __add__(self, other: "Money") -> "Money":
        if self.currency_code != other.currency_code:
            raise CurrencyMismatchError(
                from_currency=self.currency_code,
                to_currency=other.currency_code,
            )
        return Money(self.amount + other.amount, self.currency_code)

    def __sub__(self, other: "Money") -> "Money":
        if self.currency_code != other.currency_code:
            raise CurrencyMismatchError(
                from_currency=self.currency_code,
                to_currency=other.currency_code,
            )
        return Money(self.amount - other.amount, self.currency_code)


class NonNegativeMoney(Money):
    """Money dataclass used to bind amount to currency. Can be only >= 0"""

    def __init__(self, amount: Decimal, currency_code: str) -> None:
        if amount < 0:
            raise NegativeMoneyError(amount=amount)
        super().__init__(amount, currency_code)
