from decimal import Decimal
from uuid import UUID


class DomainError(Exception):
    pass


class UnsupportedCurrencyError(DomainError):
    def __init__(self, currency_code: str) -> None:
        self.currency_code = currency_code
        super().__init__(f"Unsupported currency code '{currency_code}'.")


class WebhookNotFoundError(DomainError):
    def __init__(self, webhook_id: UUID) -> None:
        self.webhook_id = webhook_id
        super().__init__(f"Webhook with ID {webhook_id} not found.")


class WebhookSubscriptionNotFoundError(DomainError):
    def __init__(self, subscription_id: UUID) -> None:
        self.subscription_id = subscription_id
        super().__init__(f"Webhook subscription with ID {subscription_id} not found.")


class UnsupportedWebhookEventTypeError(DomainError):
    def __init__(self, event_type: str) -> None:
        self.event_type = event_type
        super().__init__(f"Unsupported webhook event type '{event_type}'.")


class DuplicateWebhookSubscriptionError(DomainError):
    def __init__(self, webhook_id: UUID, event_type: str) -> None:
        self.webhook_id = webhook_id
        self.event_type = event_type
        super().__init__(f"Webhook {webhook_id} is already subscribed to '{event_type}'.")


class NotificationNotFoundError(DomainError):
    def __init__(self, notification_id: UUID) -> None:
        self.notification_id = notification_id
        super().__init__(f"Notification with ID {notification_id} not found.")


class WalletCurrencyImmutableError(DomainError):
    def __init__(self, current_currency: str, requested_currency: str) -> None:
        self.current_currency = current_currency
        self.requested_currency = requested_currency
        super().__init__(
            f"Wallet currency is immutable: wallet is denominated in {current_currency}, "
            f"cannot replace with {requested_currency}."
        )


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


class AmountPrecisionError(DomainError):
    def __init__(self, amount: Decimal, currency_code: str, decimals: int) -> None:
        self.amount = amount
        self.currency_code = currency_code
        self.decimals = decimals
        super().__init__(f"{currency_code} allows {decimals} fraction digits, got {amount}.")


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
