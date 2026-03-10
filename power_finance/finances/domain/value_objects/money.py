from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Money:
    """
    Money dataclass used to bind amount to currency.
    """

    amount: Decimal
    currency_code: str

    def __str__(self):
        return f"{self.amount} {self.currency_code}"

    def __add__(self, other: "Money"):
        if self.currency_code != other.currency_code:
            raise ValueError("Currency mismatch")

        return Money(self.amount + other.amount, self.currency_code)

    def __sub__(self, other: "Money"):
        if self.currency_code != other.currency_code:
            raise ValueError("Currency mismatch")

        return Money(self.amount - other.amount, self.currency_code)