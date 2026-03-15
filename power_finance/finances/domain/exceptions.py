from decimal import Decimal


class UnsupportedCurrencyError(Exception):
    """Raised when the currency that was requested does not exist or is not supported"""

    def __init__(self, currency_code: str) -> None:
        self.currency_code = currency_code

        super().__init__(f"Unsupported currency code '{currency_code}' encountered.")


class CurrencyMismatchException(Exception):
    """Raised when money operations with two different currencies are called"""

    def __init__(self, from_currency: str, to_currency: str) -> None:
        self.from_currency = from_currency
        self.to_currency = to_currency

        super().__init__(f"Currency '{from_currency}' is different from currency '{to_currency}'.")


class InsufficientFundsException(Exception):
    """Raised when trying to operate with insufficient funds"""

    def __init__(self, amount: Decimal, available: Decimal) -> None:
        self.amount = amount
        self.available = available

        super().__init__(f"Insufficient funds amount '{amount}' from available '{available}'.")