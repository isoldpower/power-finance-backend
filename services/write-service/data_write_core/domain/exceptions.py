from decimal import Decimal
from uuid import UUID


class DomainError(Exception):
    pass


class UnsupportedCurrencyError(DomainError):
    def __init__(self, currency_code: str) -> None:
        self.currency_code = currency_code
        super().__init__(f"Unsupported currency code '{currency_code}'.")


class CurrencyMismatchError(DomainError):
    def __init__(self, from_currency: str, to_currency: str) -> None:
        self.from_currency = from_currency
        self.to_currency = to_currency
        super().__init__(f"Currency code mismatch: expected {from_currency} but got {to_currency}.")


class InsufficientFundsError(DomainError):
    def __init__(self, amount: Decimal, available: Decimal) -> None:
        self.amount = amount
        self.available = available
        super().__init__(f"Insufficient funds: requested {amount}, available {available}.")


class NegativeMoneyError(DomainError):
    def __init__(self, amount: Decimal) -> None:
        self.amount = amount
        super().__init__(f"Money amount must be non-negative, got {amount}.")


class EventCollectorClosedError(DomainError):
    def __init__(self) -> None:
        super().__init__("Cannot collect events from a closed collector.")


class InvalidTransactionAmountError(DomainError):
    def __init__(self, amount: Decimal) -> None:
        self.amount = amount
        super().__init__(f"Transaction amount must be non-zero, got {amount}.")


class TransactionDoesNotBelongToWalletError(DomainError):
    def __init__(self, transaction_id: UUID, wallet_id: UUID) -> None:
        self.transaction_id = transaction_id
        self.wallet_id = wallet_id
        super().__init__(f"Transaction {transaction_id} does not belong to wallet {wallet_id}.")


class TransactionAlreadyCancelledError(DomainError):
    def __init__(self, transaction_id: UUID) -> None:
        self.transaction_id = transaction_id
        super().__init__(f"Transaction {transaction_id} has already been cancelled.")


class ConflictingTransactionDataError(DomainError):
    def __init__(self) -> None:
        super().__init__("Transaction cannot both cancel and adjust another transaction.")


class TransactionAlreadyAdjustedError(DomainError):
    def __init__(self, transaction_id: UUID) -> None:
        self.transaction_id = transaction_id
        super().__init__(f"Transaction {transaction_id} has already been adjusted.")


class CannotCancelInverseTransactionError(DomainError):
    def __init__(self, transaction_id: UUID) -> None:
        self.transaction_id = transaction_id
        super().__init__(
            f"Transaction {transaction_id} is itself an inverse and cannot be cancelled."
        )


class CannotAdjustAdjustmentTransactionError(DomainError):
    def __init__(self, transaction_id: UUID) -> None:
        self.transaction_id = transaction_id
        super().__init__(
            f"Transaction {transaction_id} is itself an adjustment and cannot be adjusted."
        )
